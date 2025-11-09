/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Hitachi Brand Colors
        hitachi: {
          red: '#E60012',        // Hitachi Red (Primary Brand Color)
          'red-dark': '#C40010',
          'red-light': '#FF1A2E',
          navy: '#002E6D',       // Hitachi Navy Blue
          'navy-dark': '#001E47',
          'navy-light': '#003D8F',
          gray: {
            50: '#F8F9FA',
            100: '#F1F3F5',
            200: '#E9ECEF',
            300: '#DEE2E6',
            400: '#CED4DA',
            500: '#ADB5BD',
            600: '#6C757D',
            700: '#495057',
            800: '#343A40',
            900: '#212529',
          },
          blue: '#0066CC',       // Accent Blue
          green: '#00A676',      // Success Green
          orange: '#FF6B35',     // Warning Orange
          purple: '#6B4E9A',     // Accent Purple
        },
        // Semantic Colors
        primary: {
          50: '#FFF1F2',
          100: '#FFE1E3',
          200: '#FFC7CB',
          300: '#FF9DA3',
          400: '#FF646D',
          500: '#FF2B37',
          600: '#E60012',        // Hitachi Red
          700: '#C40010',
          800: '#9E000D',
          900: '#7A000A',
        },
        secondary: {
          50: '#E6F0FF',
          100: '#CCE0FF',
          200: '#99C2FF',
          300: '#66A3FF',
          400: '#3385FF',
          500: '#0066CC',
          600: '#0052A3',
          700: '#003D7A',
          800: '#002E6D',        // Hitachi Navy
          900: '#001E47',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        display: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        'hitachi-sm': '0 1px 2px 0 rgba(230, 0, 18, 0.05)',
        'hitachi': '0 4px 6px -1px rgba(230, 0, 18, 0.1), 0 2px 4px -1px rgba(230, 0, 18, 0.06)',
        'hitachi-md': '0 10px 15px -3px rgba(230, 0, 18, 0.1), 0 4px 6px -2px rgba(230, 0, 18, 0.05)',
        'hitachi-lg': '0 20px 25px -5px rgba(230, 0, 18, 0.1), 0 10px 10px -5px rgba(230, 0, 18, 0.04)',
        'hitachi-xl': '0 25px 50px -12px rgba(230, 0, 18, 0.25)',
        'card': '0 2px 8px rgba(0, 0, 0, 0.08)',
        'card-hover': '0 4px 16px rgba(0, 0, 0, 0.12)',
      },
      animation: {
        'slide-up': 'slideUp 0.3s ease-out',
        'slide-down': 'slideDown 0.3s ease-out',
        'fade-in': 'fadeIn 0.2s ease-in',
        'scale-in': 'scaleIn 0.2s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: 0 },
          '100%': { transform: 'translateY(0)', opacity: 1 },
        },
        slideDown: {
          '0%': { transform: 'translateY(-10px)', opacity: 0 },
          '100%': { transform: 'translateY(0)', opacity: 1 },
        },
        fadeIn: {
          '0%': { opacity: 0 },
          '100%': { opacity: 1 },
        },
        scaleIn: {
          '0%': { transform: 'scale(0.95)', opacity: 0 },
          '100%': { transform: 'scale(1)', opacity: 1 },
        },
      },
    },
  },
  plugins: [],
}

