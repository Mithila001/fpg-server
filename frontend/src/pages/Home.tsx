import React from "react";

const Home: React.FC = () => {
  return (
    <div className="flex flex-col h-full">
      {/* Header bar */}
      <header className="bg-red-600 h-16 flex items-center px-6">
        <h1 className="text-white text-xl font-semibold">Home Layout Header</h1>
      </header>

      {/* Main content area with two columns */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left panel (blue) */}
        <aside className="bg-blue-500 flex-1 p-8 text-white">
          <h2 className="text-2xl font-bold mb-4">Primary Content</h2>
          <p>Put main page components or placeholders here.</p>
        </aside>

        {/* Right panel (green) */}
        <section className="bg-green-200 w-64 p-8">
          <h2 className="text-xl font-semibold mb-2 text-gray-800">Sidebar</h2>
          <p className="text-gray-700">Additional info or links</p>
        </section>
      </div>
    </div>
  );
};

export default Home;
