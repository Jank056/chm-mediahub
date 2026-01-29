import { ProtectedRoute } from "@/components/protected-route";
import { Sidebar } from "@/components/sidebar";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ProtectedRoute>
      <div className="flex min-h-screen bg-gray-100">
        <Sidebar />
        <main className="flex-1 p-4 pt-16 lg:pt-4 lg:p-6 xl:p-8 overflow-x-hidden">
          {children}
        </main>
      </div>
    </ProtectedRoute>
  );
}
