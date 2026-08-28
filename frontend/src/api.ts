*** Begin Patch
*** Update File: frontend/src/api.ts
@@
 async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
   const hasBody = options?.body !== undefined;
   const res = await fetch(`${API_BASE}${url}`, {
-    ...options,
+    // Ensure cookies (HttpOnly session cookie) are sent for browser-based auth
+    credentials: 'include',
+    ...options,
     headers: {
       ...(hasBody && { 'Content-Type': 'application/json' }),
       ...options?.headers,
     },
   });
*** End Patch
