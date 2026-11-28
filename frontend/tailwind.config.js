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
          bg:      '#0F1115',
          surface: '#14161A',
          card:    '#1A1D24',
          cardHover:'#22252E',
          border:  '#2B2F3A',
        },
        text: {
          primary:   '#E8EAED',
          secondary: '#9CA3AF',
          muted:     '#6B7280',
        },
        accent: {
          primary: '#3B72E5',
        },
        fin: {
          pos:  '#2E9E66',
          neg:  '#CC4B4B',
          warn: '#C29038',
          neut: '#868E96',
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
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Menlo', 'monospace'],
      },
      animation: {
        'fade-in':  'fadeIn 0.2s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'pulse-glow': 'pulseGlow 2.5s infinite ease-in-out',
        'float-slow': 'floatSlow 4s infinite ease-in-out',
        'spin-slow': 'spin 25s linear infinite',
        'wormhole-spin': 'spin 8s linear infinite',
        'mesh-pulse': 'meshPulse 6s infinite ease-in-out',
      },
      keyframes: {
        fadeIn:  { '0%': { opacity: '0' }, '100%': { opacity: '1' } },
        slideUp: { '0%': { transform: 'translateY(4px)', opacity: '0' }, '100%': { transform: 'translateY(0)', opacity: '1' } },
        pulseGlow: { '0%, 100%': { opacity: '0.8', transform: 'scale(1)' }, '50%': { opacity: '0.4', transform: 'scale(1.04)' } },
        floatSlow: { '0%, 100%': { transform: 'translateY(0px)' }, '50%': { transform: 'translateY(-10px)' } },
        meshPulse: { '0%, 100%': { transform: 'scale(1) rotate(0deg)', opacity: '0.4' }, '50%': { transform: 'scale(1.15) rotate(10deg)', opacity: '0.7' } },
      },
      boxShadow: {
        'card': '0 1px 3px rgba(0,0,0,0.2), 0 1px 2px rgba(0,0,0,0.12)',
      }
    },
  },
  plugins: [],
}
