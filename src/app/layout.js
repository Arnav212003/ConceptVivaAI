import "./globals.css";
import AnalyticsTracker from "@/components/AnalyticsTracker";
import { AuthProvider } from "@/components/AuthProvider";
import Navbar from "@/components/Navbar";

export const metadata = {
  title: "ConceptVivaAI",
  description:
    "AI-powered topic-wise mock interview, DSA practice, and project challenge platform",
};

export const viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="overflow-x-hidden">
        <AuthProvider>
          <AnalyticsTracker />
          <Navbar />
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
