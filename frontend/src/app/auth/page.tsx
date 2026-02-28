"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth-store";
import toast from "react-hot-toast";

export default function AuthPage() {
  const router = useRouter();
  const { login, register } = useAuthStore();
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (isLogin) {
        await login(email, password);
        toast.success("Zalogowano!");
      } else {
        await register(email, password, fullName);
        toast.success("Konto utworzone!");
      }
      router.push("/dashboard");
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Wystapil blad";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-dark-900 px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-brand-600 mb-4">
            <span className="text-2xl font-bold text-white">A</span>
          </div>
          <h1 className="text-3xl font-bold text-white">AutoShorts</h1>
          <p className="mt-2 text-dark-200">
            Automatyczne generowanie faceless short-video
          </p>
        </div>

        {/* Form */}
        <div className="card">
          <div className="flex mb-6">
            <button
              onClick={() => setIsLogin(true)}
              className={`flex-1 py-2 text-center rounded-lg text-sm font-medium transition-colors ${
                isLogin ? "bg-brand-600 text-white" : "text-dark-200 hover:text-white"
              }`}
            >
              Logowanie
            </button>
            <button
              onClick={() => setIsLogin(false)}
              className={`flex-1 py-2 text-center rounded-lg text-sm font-medium transition-colors ${
                !isLogin ? "bg-brand-600 text-white" : "text-dark-200 hover:text-white"
              }`}
            >
              Rejestracja
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {!isLogin && (
              <div>
                <label className="label">Imie i nazwisko</label>
                <input
                  type="text"
                  className="input-field"
                  placeholder="Jan Kowalski"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                />
              </div>
            )}

            <div>
              <label className="label">E-mail</label>
              <input
                type="email"
                className="input-field"
                placeholder="jan@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div>
              <label className="label">Haslo</label>
              <input
                type="password"
                className="input-field"
                placeholder="Min. 8 znakow"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
              />
            </div>

            <button type="submit" className="btn-primary w-full" disabled={loading}>
              {loading ? "Przetwarzanie..." : isLogin ? "Zaloguj sie" : "Utworz konto"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
