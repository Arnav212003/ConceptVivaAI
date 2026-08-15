import nextVitals from "eslint-config-next/core-web-vitals";

const config = [
  ...nextVitals,
  {
    ignores: ["node_modules/**", ".next/**", "out/**", "dist/**", "build/**"],
    rules: {
      // These components intentionally hydrate persisted client-only state from
      // localStorage on mount. The rule is too strict for that browser boundary.
      "react-hooks/set-state-in-effect": "off",
      "react/no-unescaped-entities": "off",
    },
  },
];

export default config;
