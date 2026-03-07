import React from "react";

const About: React.FC = () => {
  return (
    <div className="space-y-6">
      <h1 className="text-4xl font-bold text-gray-800 dark:text-gray-100">About Us</h1>
      <p className="text-gray-600 dark:text-gray-300">
        House Plan Generator is a tool built to help homeowners and designers quickly draft and
        visualize custom floor plans. Our mission is to make home design accessible to everyone.
      </p>
    </div>
  );
};

export default About;
