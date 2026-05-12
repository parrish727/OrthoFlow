"use client";

import { CheckCircle } from "lucide-react";
import Link from "next/link";

export default function Pricing() {
  const plans = [
    {
      name: "Starter",
      price: "$99",
      period: "/month",
      description: "Perfect for small practices",
      features: [
        "Up to 100 invoices/month",
        "Basic OCR processing",
        "Email support",
        "Data export",
      ],
    },
    {
      name: "Professional",
      price: "$299",
      period: "/month",
      description: "For growing practices",
      features: [
        "Up to 500 invoices/month",
        "Advanced AI validation",
        "Priority support",
        "API access",
        "Custom integrations",
      ],
      highlighted: true,
    },
    {
      name: "Enterprise",
      price: "Custom",
      period: "",
      description: "For large organizations",
      features: [
        "Unlimited invoices",
        "Full customization",
        "Dedicated support",
        "Custom workflows",
        "SLA guarantee",
      ],
    },
  ];

  return (
    <div className="w-full overflow-hidden">
      {/* Header */}
      <section className="section-wrapper bg-gradient-to-br from-blue-50 to-white py-12 sm:py-16 md:py-24">
        <div className="section-inner text-center">
          <h1 className="heading-responsive text-gray-900 mb-4">
            Simple, Transparent Pricing
          </h1>
          <p className="text-base sm:text-lg text-gray-600 max-w-2xl mx-auto">
            Choose the perfect plan for your practice.
          </p>
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="section-wrapper py-12 sm:py-16 md:py-24">
        <div className="section-inner">
          <div className="mobile-stack md:flex md:gap-6 md:justify-center">
            {plans.map((plan, idx) => (
              <div
                key={idx}
                className={`card-mobile flex flex-col ${
                  plan.highlighted ? "ring-2 ring-blue-600 md:scale-105" : ""
                }`}
              >
                <h3 className="font-bold text-xl sm:text-2xl text-gray-900">
                  {plan.name}
                </h3>
                <p className="text-sm text-gray-600 mt-2">{plan.description}</p>

                <div className="my-6 sm:my-8">
                  <span className="text-3xl sm:text-4xl font-bold text-gray-900">
                    {plan.price}
                  </span>
                  {plan.period && (
                    <span className="text-gray-600 ml-2">{plan.period}</span>
                  )}
                </div>

                <div className="mobile-stack mb-8 flex-1">
                  {plan.features.map((feature, fidx) => (
                    <div key={fidx} className="flex gap-2 sm:gap-3">
                      <CheckCircle className="w-5 h-5 sm:w-6 sm:h-6 text-green-600 flex-shrink-0 mt-0.5" />
                      <span className="text-sm sm:text-base text-gray-700">
                        {feature}
                      </span>
                    </div>
                  ))}
                </div>

                <Link
                  href="/signup"
                  className={`button-mobile mt-auto ${
                    plan.highlighted
                      ? "bg-blue-600 text-white hover:bg-blue-700"
                      : "border border-gray-300 text-gray-700 hover:bg-gray-50"
                  }`}
                >
                  Get Started
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}