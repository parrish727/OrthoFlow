"use client";

import { CheckCircle } from "lucide-react";

export default function Features() {
  const features = [
    {
      title: "Intelligent OCR",
      description:
        "Advanced optical character recognition to extract invoice data accurately.",
    },
    {
      title: "AI Validation",
      description:
        "Machine learning models verify data consistency and catch errors.",
    },
    {
      title: "Real-time Processing",
      description: "Process multiple invoices simultaneously without delays.",
    },
    {
      title: "Integration API",
      description:
        "Connect with your EHR and accounting systems seamlessly.",
    },
    {
      title: "Audit Trail",
      description:
        "Complete logging of all processing steps for compliance.",
    },
    {
      title: "Custom Rules",
      description:
        "Set up business rules specific to your practice workflow.",
    },
  ];

  return (
    <div className="w-full overflow-hidden">
      {/* Header */}
      <section className="section-wrapper bg-gradient-to-br from-blue-50 to-white py-12 sm:py-16 md:py-24">
        <div className="section-inner text-center">
          <h1 className="heading-responsive text-gray-900 mb-4">Features</h1>
          <p className="text-base sm:text-lg text-gray-600 max-w-2xl mx-auto">
            Everything you need to modernize your invoice processing.
          </p>
        </div>
      </section>

      {/* Features Grid */}
      <section className="section-wrapper py-12 sm:py-16 md:py-24">
        <div className="section-inner">
          <div className="mobile-grid">
            {features.map((feature, idx) => (
              <div key={idx} className="card-mobile">
                <div className="flex gap-3 sm:gap-4 mb-3 sm:mb-4">
                  <CheckCircle className="w-6 h-6 sm:w-8 sm:h-8 text-blue-600 flex-shrink-0" />
                  <h3 className="font-semibold text-gray-900 text-base sm:text-lg">
                    {feature.title}
                  </h3>
                </div>
                <p className="text-sm sm:text-base text-gray-600">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}