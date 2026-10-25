// Cores do Tailwind apontam para os tokens (tokens.css), em triplet RGB para
  // os modificadores de opacidade funcionarem (bg-fundo/95). "fundo" e não
  // "base": uma cor chamada base colide com o utilitário de tamanho text-base.
  const token = (nome) => `rgb(var(--${nome}-rgb) / <alpha-value>)`;
  module.exports = {
    content: ['./src/spectra_link_guard/web/static/*.{html,js}', './src/spectra_link_guard/web/parciais/*.html'],
    plugins: [require('@tailwindcss/forms')],
    theme: {
      extend: {
        colors: {
          fundo:         token("base"),
          sup:           token("base-2"),
          "sup-2":       token("base-3"),
          "sup-3":       token("base-4"),
          linha:         token("linha"),
          "linha-forte": token("linha-forte"),
          txt:           token("texto"),
          "txt-2":       token("texto-2"),
          "txt-3":       token("texto-3"),
          marca:         token("primaria"),
          "marca-claro": token("primaria-clara"),
          sage:          token("secundaria"),
          amarelo:       token("terciaria"),
          perigo:        token("perigo"),
          "sobre-marca": token("sobre-primaria"),
        },
        fontFamily: {
          display: ['"Hanken Grotesk"', "system-ui", "sans-serif"],
          corpo:   ['"Inter"', "system-ui", "sans-serif"],
          mono:    ['"JetBrains Mono"', "ui-monospace", "monospace"],
        },
        boxShadow: {
          suave: "0 18px 40px -24px rgba(0,0,0,.9)",
          alta:  "0 30px 60px -30px rgba(0,0,0,1)",
        },
      },
    },
  };
