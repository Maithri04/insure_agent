import React from "react";

export default function FlashCard({
  title = "Insure Agent",
  subtitle = "AI-powered approval assistant",
  large = false,
}) {
  return (
    <div
      className={`text-white rounded-lg shadow-sm transition-colors ${
        large
          ? "p-10 md:p-14 bg-gradient-to-br from-blue-950 via-blue-800 to-sky-500"
          : "p-4 bg-gradient-to-br from-blue-900 via-blue-700 to-sky-500"
      }`}
    >
      <div className={`flex items-start ${large ? "gap-5" : "gap-3"}`}>
        <span
          className={`inline-flex items-center justify-center rounded-md bg-white/20 font-semibold ${
            large ? "h-16 w-16 text-2xl" : "h-8 w-8 text-sm"
          }`}
        >
          IA
        </span>
        <div>
          <p className={large ? "font-extrabold text-6xl md:text-7xl leading-tight tracking-tight" : "font-semibold"}>
            {title}
          </p>
          <p className={large ? "text-2xl md:text-3xl text-blue-100 mt-3 font-medium" : "text-xs text-blue-100 mt-0.5"}>
            {subtitle}
          </p>
        </div>
      </div>
    </div>
  );
}
