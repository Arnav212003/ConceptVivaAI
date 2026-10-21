import nextVitals from "eslint-config-next/core-web-vitals";

const config = [
  // A config object with only `ignores` is a global ignore in flat config.
  {
    ignores: [
      "node_modules/**", ".next/**", "out/**", "dist/**", "build/**",
      "backend/**", "coverage/**", "playwright-report/**", "test-results/**",
    ],
  },
  ...nextVitals,
  {
    rules: {
      // These components intentionally hydrate persisted client-only state from
      // localStorage on mount. The rule is too strict for that browser boundary.
      "react-hooks/set-state-in-effect": "off",
      "react/no-unescaped-entities": "off",
    },
  },
];

export default config;
