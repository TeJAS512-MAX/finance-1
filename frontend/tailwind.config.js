/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        terminal: {
          bg:       '#070A0F',
          surface:  '#0C111B',
          card:     '#101724',
          cardHover:'#162032',
          border:   '#1E293B',
        },
        text: {
          primary:   '#F1F5F9',
          secondary: '#94A3B8',
          muted:     '#64748B',
        },
        accent: {
          primary: '#3B82F6',
          cyan:    '#22D3EE',
        },
        fin: {
          pos:  '#10B981',
          neg:  '#F43F5E',
          warn: '#F59E0B',
          neut: '#94A3B8',
        },
        darkbg: '#020617',
        darkerbg: '#080b12',
        panel: '#0f172a',
        panelcard: '#111726',
        panelborder: '#1e293b',
        brand: {
          50: '#ecfdf5',
          300: '#6ee7b7',
          400: '#34d399',
          500: '#10b981',
          600: '#059669',
          900: '#064e3b',
        },
        accentcyan: '#22d3ee',
        accentpurple: '#8b5cf6',
        warningamber: '#f59e0b',
        dangerrose: '#f43f5e',
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'Menlo', 'monospace'],
      },
      animation: {
        'fade-in':     'fadeIn 0.28s cubic-bezier(0.22, 1, 0.36, 1)',
        'slide-up':    'slideUp 0.36s cubic-bezier(0.22, 1, 0.36, 1)',
        'page-slide':  'pageSlide 0.34s cubic-bezier(0.22, 1, 0.36, 1)',
        'ticker':      'tickerScroll 42s linear infinite',
        'pulse-glow':  'pulseGlow 2.8s infinite ease-in-out',
        'float-slow':  'floatSlow 5s infinite ease-in-out',
        'spin-slow':   'spin 25s linear infinite',
        'wormhole-spin': 'spin 8s linear infinite',
        'mesh-pulse':  'meshPulse 6s infinite ease-in-out',
      },
      keyframes: {
        fadeIn:       { '0%': { opacity: '0' }, '100%': { opacity: '1' } },
        slideUp:      { '0%': { transform: 'translateY(8px)', opacity: '0' }, '100%': { transform: 'translateY(0)', opacity: '1' } },
        pageSlide:    { '0%': { transform: 'translateX(14px)', opacity: '0' }, '100%': { transform: 'translateX(0)', opacity: '1' } },
        tickerScroll: { '0%': { transform: 'translateX(0)' }, '100%': { transform: 'translateX(-50%)' } },
        pulseGlow:    { '0%, 100%': { opacity: '0.9', transform: 'scale(1)' }, '50%': { opacity: '0.5', transform: 'scale(1.04)' } },
        floatSlow:    { '0%, 100%': { transform: 'translateY(0px)' }, '50%': { transform: 'translateY(-8px)' } },
        meshPulse:    { '0%, 100%': { transform: 'scale(1) rotate(0deg)', opacity: '0.4' }, '50%': { transform: 'scale(1.15) rotate(10deg)', opacity: '0.7' } },
      },
      boxShadow: {
        'card': '0 10px 30px -12px rgba(2, 6, 23, 0.75), inset 0 1px 0 0 rgba(255, 255, 255, 0.05)',
      }
    },
  },
  plugins: [],
}
