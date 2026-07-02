import "./globals.css";
import Navbar from "@/components/Navbar";

export const metadata = {
  title: "ConceptVivaAI",
  description:
    "AI-powered topic-wise mock interview, DSA practice, and project challenge platform",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <Navbar />
        {children}
      </body>
    </html>
  );
}