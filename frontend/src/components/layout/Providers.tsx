"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "react-hot-toast";
import { useEffect, useState } from "react";
import { useAuthStore } from "@/store/auth-store";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

export function Providers({ children }: { children: React.ReactNode }) {
  const initialize = useAuthStore((s) => s.initialize);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    initialize().then(() => setReady(true));
  }, [initialize]);

  if (!ready) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-dark-900">
        <div className="animate-pulse text-brand-400 text-xl font-semibold">
          AutoShorts
        </div>
      </div>
    );
  }

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: "#25262B",
            color: "#f0f0f5",
            border: "1px solid #373A40",
          },
        }}
      />
    </QueryClientProvider>
  );
}
