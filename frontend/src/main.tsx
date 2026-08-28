*** Begin Patch
*** Update File: frontend/src/main.tsx
@@
 import { App } from './App';
+import Login from './pages/Login';
@@
   <StrictMode>
-    <PushSubscriptionProvider>
-      <App />
-    </PushSubscriptionProvider>
+    <PushSubscriptionProvider>
+      <App />
+    </PushSubscriptionProvider>
   </StrictMode>
 );
*** End Patch
