"""Fanout module wrapping bot execution logic."""

from __future__ import annotations

import asyncio
import logging
import time

from app.fanout.base import FanoutModule

logger = logging.getLogger(__name__)


def _derive_path_bytes_per_hop(paths: object, path_value: str | None) -> int | None:
    """Derive hop width from the first serialized message path when possible."""
    if not isinstance(path_value, str) or not path_value:
        return None
    if not isinstance(paths, list) or not paths:
        return None

    first_path = paths[0]
    if not isinstance(first_path, dict):
        return None

    path_hops = first_path.get("path_len")
    if not isinstance(path_hops, int) or path_hops <= 0:
        return None

    path_hex_chars = len(path_value)
    if path_hex_chars % 2 != 0:
        return None

    path_bytes = path_hex_chars // 2
    if path_bytes % path_hops != 0:
        return None

    hop_width = path_bytes // path_hops
    if hop_width not in (1, 2, 3):
        return None

    return hop_width


class BotModule(FanoutModule):
    """Wraps a single bot's code execution and response routing.

    Each BotModule represents one bot configuration. It receives decoded
    messages via ``on_message``, executes the bot's Python code in a
    background task (after a 2-second settle delay), and sends any response
    back through the radio.
    
    Channel filtering and rate limiting are applied based on bot config.
    """

    def __init__(self, config_id: str, config: dict, *, name: str = "Bot") -> None:
        super().__init__(config_id, config, name=name)
        self._tasks: set[asyncio.Task] = set()
        self._active = True
        
        # Extract channel filter config (safe defaults: empty allowlist, no DMs)
        self._channel_filter = config.get("channel_filter", {})
        self._filter_mode = self._channel_filter.get("mode", "allowlist")
        self._allowed_channels = set(self._channel_filter.get("channels", []))
        self._include_dms = self._channel_filter.get("include_dms", False)
        
        # Extract rate limit config (default: 10 messages per 60 seconds)
        self._rate_limit = config.get("rate_limit", {})
        self._rate_limit_messages = self._rate_limit.get("messages_per_60sec", 10)
        self._message_timestamps: list[float] = []

    async def stop(self) -> None:
        self._active = False
        for task in self._tasks:
            task.cancel()
        # Wait briefly for tasks to acknowledge cancellation
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    def _should_process_message(self, data: dict) -> bool:
        """Check if message passes channel filter."""
        msg_type = data.get("type", "")
        is_dm = msg_type == "PRIV"
        conversation_key = data.get("conversation_key", "")
        
        # Filter DMs based on include_dms flag
        if is_dm:
            if not self._include_dms:
                logger.debug(
                    "Bot '%s' filtered DM from %s (include_dms=false)",
                    self.name,
                    conversation_key[:12] if conversation_key else "(unknown)",
                )
                return False
            return True
        
        # Filter channels based on allowlist/blocklist mode
        if self._filter_mode == "allowlist":
            if conversation_key not in self._allowed_channels:
                logger.debug(
                    "Bot '%s' filtered channel message from %s (not in allowlist)",
                    self.name,
                    conversation_key[:12] if conversation_key else "(unknown)",
                )
                return False
        elif self._filter_mode == "blocklist":
            if conversation_key in self._allowed_channels:
                logger.debug(
                    "Bot '%s' filtered channel message from %s (in blocklist)",
                    self.name,
                    conversation_key[:12] if conversation_key else "(unknown)",
                )
                return False
        # mode == "all" passes everything (already filtered by DMs above)
        
        return True
    
    def _check_rate_limit(self) -> bool:
        """Check if rate limit allows processing this message.
        
        Returns True if message should be processed, False if rate limit exceeded.
        Prunes old timestamps outside the 60-second window.
        """
        now = time.monotonic()
        window_start = now - 60.0
        
        # Remove timestamps outside the 60-second window
        self._message_timestamps = [ts for ts in self._message_timestamps if ts > window_start]
        
        # Check if we've exceeded the limit
        if len(self._message_timestamps) >= self._rate_limit_messages:
            logger.debug(
                "Bot '%s' rate limited: %d messages in last 60s (limit: %d)",
                self.name,
                len(self._message_timestamps),
                self._rate_limit_messages,
            )
            return False
        
        # Record this message
        self._message_timestamps.append(now)
        return True

    async def on_message(self, data: dict) -> None:
        """Kick off bot execution in a background task so we don't block dispatch.
        
        Messages are filtered by channel allowlist/blocklist and rate-limited
        before execution is scheduled.
        """
        # Apply channel filter
        if not self._should_process_message(data):
            return
        
        # Apply rate limiting
        if not self._check_rate_limit():
            return
        
        task = asyncio.create_task(self._run_for_message(data))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _run_for_message(self, data: dict) -> None:
        from app.fanout.bot_exec import (
            BOT_EXECUTION_TIMEOUT,
            execute_bot_code,
            process_bot_response,
        )

        code = self.config.get("code", "")
        if not code or not code.strip():
            return

        msg_type = data.get("type", "")
        is_dm = msg_type == "PRIV"
        conversation_key = data.get("conversation_key", "")
        logger.debug(
            "Bot '%s' starting for type=%s conversation=%s outgoing=%s",
            self.name,
            msg_type or "unknown",
            conversation_key[:12] if conversation_key else "(none)",
            bool(data.get("outgoing", False)),
        )

        # Extract bot parameters from broadcast data
        if is_dm:
            sender_key = data.get("sender_key") or conversation_key
            is_outgoing = data.get("outgoing", False)
            message_text = data.get("text", "")
            channel_key = None
            channel_name = None

            # Outgoing DMs: sender is us, not the contact
            if is_outgoing:
                sender_name = None
            else:
                sender_name = data.get("sender_name")
                if sender_name is None:
                    from app.repository import ContactRepository

                    contact = await ContactRepository.get_by_key(conversation_key)
                    sender_name = contact.name if contact else None
        else:
            sender_key = None
            is_outgoing = bool(data.get("outgoing", False))
            sender_name = data.get("sender_name")
            channel_key = conversation_key

            channel_name = data.get("channel_name")
            if channel_name is None:
                from app.repository import ChannelRepository

                channel = await ChannelRepository.get_by_key(conversation_key)
                channel_name = channel.name if channel else None

            # Strip "sender: " prefix from channel message text
            text = data.get("text", "")
            if sender_name and text.startswith(f"{sender_name}: "):
                message_text = text[len(f"{sender_name}: ") :]
            else:
                message_text = text

        sender_timestamp = data.get("sender_timestamp")
        path_value = data.get("path")
        paths = data.get("paths")
        # Message model serializes paths as list of dicts; extract first path string
        if path_value is None and paths and isinstance(paths, list) and len(paths) > 0:
            path_value = paths[0].get("path") if isinstance(paths[0], dict) else None
        path_bytes_per_hop = _derive_path_bytes_per_hop(paths, path_value)
        packet_hash = data.get("packet_hash")
        # Resolved region name (None for unscoped flood or a transport code that
        # matched no known region). `scoped` disambiguates None: a transport code
        # was present iff the message carried a regional flood scope. This is set
        # for scoped DMs too (flood-direct messages can carry a scope).
        region = data.get("region")
        scoped = data.get("transport_code") is not None

        # Wait for message to settle (allows retransmissions to be deduped)
        await asyncio.sleep(2)

        # Execute bot code in thread pool with timeout
        from app.fanout.bot_exec import _bot_executor, _bot_semaphore

        async with _bot_semaphore:
            loop = asyncio.get_running_loop()
            try:
                response = await asyncio.wait_for(
                    loop.run_in_executor(
                        _bot_executor,
                        execute_bot_code,
                        code,
                        sender_name,
                        sender_key,
                        message_text,
                        is_dm,
                        channel_key,
                        channel_name,
                        sender_timestamp,
                        path_value,
                        is_outgoing,
                        path_bytes_per_hop,
                        packet_hash,
                        region,
                        scoped,
                    ),
                    timeout=BOT_EXECUTION_TIMEOUT,
                )
            except TimeoutError:
                logger.warning("Bot '%s' execution timed out", self.name)
                return
            except Exception:
                logger.exception("Bot '%s' execution error", self.name)
                return

        if response and self._active:
            await process_bot_response(response, is_dm, sender_key or "", channel_key)

    @property
    def status(self) -> str:
        """Return module status."""
        return "connected"
