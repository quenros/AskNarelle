import React from "react";
import Link from "next/link";

const ForbiddenPage: React.FC = () => {
  return (
    <div className="flex items-center justify-center h-screen bg-gray-100">
      <div className="bg-white p-10 rounded-lg shadow-lg text-center">
        <h1 className="text-6xl font-bold text-red-600 font-nunito">403</h1>
        <h2 className="text-2xl mt-4 text-gray-800 font-nunito">Forbidden</h2>
        <p className="mt-2 text-gray-600 font-nunito">
          You do not have permission to access this page.
        </p>
        <Link href="/" className="mt-6 inline-block bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 font-nunito">
            Go to Home
        </Link>
      </div>
    </div>
  );
};

export default ForbiddenPage;