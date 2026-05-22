"use client";

import { useState, Suspense, lazy } from "react";
import { useRouter } from "next/navigation";

const Spline = lazy(() => import("@splinetool/react-spline"));

export default function LoginPage() {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const router = useRouter();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (password === "basis") {
      document.cookie = "basis_auth=basis; path=/; max-age=86400; SameSite=Lax";
      window.location.href = "/";
    } else {
      setError("Incorrect password");
    }
  };

  return (
    <div className="relative flex h-dvh w-full items-center justify-center overflow-hidden bg-black">
      {/* Spline background */}
      <div className="absolute inset-0 z-0" style={{ opacity: 0.5 }}>
        <Suspense fallback={<div className="h-full w-full bg-black" />}>
          <Spline
            style={{ width: "100%", height: "100%" }}
            scene="https://prod.spline.design/us3ALejTXl6usHZ7/scene.splinecode"
          />
        </Suspense>
      </div>

      {/* Gradient overlay for readability */}
      <div
        className="pointer-events-none absolute inset-0 z-10"
        style={{
          background:
            "linear-gradient(to top, #000000 0%, rgba(0,0,0,0.92) 25%, rgba(0,0,0,0.4) 55%, transparent 80%)",
        }}
      />

      {/* Login form */}
      <form
        onSubmit={handleSubmit}
        className="relative z-20 flex w-full max-w-sm flex-col gap-4 rounded-xl border border-white/10 bg-black/60 p-6 shadow-lg backdrop-blur-md"
      >
        <h1 className="text-xl font-semibold text-white">Basis</h1>
        <p className="text-sm text-white/60">Enter password to continue</p>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
          className="h-10 rounded-md border border-white/20 bg-white/5 px-3 text-sm text-white outline-none placeholder:text-white/30 focus:ring-2 focus:ring-white/30"
        />
        {error && <p className="text-sm text-red-400">{error}</p>}
        <button
          type="submit"
          className="h-10 rounded-md bg-white px-4 text-sm font-medium text-black transition-colors hover:bg-white/90"
        >
          Enter
        </button>
      </form>
    </div>
  );
}
