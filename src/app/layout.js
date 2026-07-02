import "./globals.css";

export const metadata = {
  title: "ConceptVivaAI",
  description: "AI-powered topic-wise mock interview platform",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}