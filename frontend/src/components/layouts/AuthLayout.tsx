import { Outlet } from 'react-router-dom';

/**
 * Layout for authentication pages (login, register, etc.)
 */
export default function AuthLayout() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <div className="w-full max-w-md p-8">
        <Outlet />
      </div>
    </div>
  );
}
