/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        aicte: {
          orange: '#F58220',
          'orange-hover': '#E06F0F',
          blue: '#0B3C9D',
          navy: '#0F2A5C',
          border: '#D5DBE5',
          placeholder: '#7A8699',
          error: '#C62828',
          success: '#2E7D32',
          lightbg: '#F8FAFC',
        },
      },
      fontFamily: {
        sans: ['Poppins', 'Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        card: '0 12px 36px -4px rgba(15, 42, 92, 0.18), 0 4px 16px -2px rgba(15, 42, 92, 0.08)',
        input: '0 0 0 2px rgba(245, 130, 32, 0.35)',
      },
      animation: {
        'fade-in': 'fadeIn 300ms ease-out forwards',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
};

