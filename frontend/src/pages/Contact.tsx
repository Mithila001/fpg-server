import React from "react";

const Contact: React.FC = () => {
  return (
    <div className="space-y-6">
      <h1 className="text-4xl font-bold text-gray-800 dark:text-gray-100">Contact Us</h1>
      <p className="text-gray-600 dark:text-gray-300">
        Have questions or feedback? Reach out to us at{" "}
        <a href="mailto:support@houseplan.com" className="text-blue-600 hover:underline">
          support@houseplan.com
        </a>
        .
      </p>
    </div>
  );
};

export default Contact;
