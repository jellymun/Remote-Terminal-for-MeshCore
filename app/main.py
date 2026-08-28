*** Begin Patch
*** Update File: app/main.py
@@
-from app.api_docs import API_DESCRIPTION, API_TAGS_METADATA, register_api_docs_routes
-from app.config import settings as server_settings
+from app.api_docs import API_DESCRIPTION, API_TAGS_METADATA, register_api_docs_routes
+from app.config import settings as server_settings
@@
-from app.security import add_optional_basic_auth_middleware
+from app.security import add_optional_basic_auth_middleware
+from app import auth as auth_module
@@
-register_api_docs_routes(app)
-add_optional_basic_auth_middleware(app, server_settings)
+register_api_docs_routes(app)
+# Disable the old app-wide HTTP Basic middleware so browsers can use a web form login.
+# The previous middleware was enabled via MESHCORE_BASIC_AUTH_USERNAME/PASSWORD.
+# We leave the function available, but do not call it by default in the web-login flow.
+# If you still want Basic auth for some deployments, re-enable the following line or
+# gate it behind a different configuration flag.
+# add_optional_basic_auth_middleware(app, server_settings)
+app.include_router(auth_module.router)
@@
-app.add_middleware(
-    CORSMiddleware,
-    allow_origins=["*"],
-    allow_credentials=True,
-    allow_methods=["*"],
-    allow_headers=["*"],
-)
+app.add_middleware(
+    CORSMiddleware,
+    # In production replace '*' with your frontend origin(s), e.g. https://example.com
+    allow_origins=["*"],
+    allow_credentials=True,
+    allow_methods=["*"],
+    allow_headers=["*"],
+)
*** End Patch
