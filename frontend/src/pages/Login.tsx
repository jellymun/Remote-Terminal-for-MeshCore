*** Begin Patch
*** Add File: frontend/src/pages/Login.tsx
+import React, { useState } from 'react';
+import { useNavigate } from 'react-router-dom';
+
+export default function Login() {
+  const [username, setUsername] = useState('');
+  const [password, setPassword] = useState('');
+  const [err, setErr] = useState<string | null>(null);
+  const navigate = useNavigate();
+
+  async function handleSubmit(e: React.FormEvent) {
+    e.preventDefault();
+    setErr(null);
+    const res = await fetch('/api/login', {
+      method: 'POST',
+      credentials: 'include',
+      headers: { 'Content-Type': 'application/json' },
+      body: JSON.stringify({ username, password }),
+    });
+    if (res.ok) {
+      navigate('/');
+    } else {
+      const text = await res.text();
+      setErr((text && text.length < 300) ? text : 'Login failed');
+    }
+  }
+
+  return (
+    <form onSubmit={handleSubmit} className="p-4 max-w-md mx-auto">
+      <h2 className="text-xl mb-4">Sign in</h2>
+      {err && <div className="text-red-600 mb-2">{err}</div>}
+      <label className="block mb-2">
+        <div className="text-sm">Username</div>
+        <input value={username} onChange={(e) => setUsername(e.target.value)} className="input" />
+      </label>
+      <label className="block mb-4">
+        <div className="text-sm">Password</div>
+        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="input" />
+      </label>
+      <button type="submit" className="btn">Log in</button>
+    </form>
+  );
+}
+
*** End Patch
