"use client";

import Link from "next/link";
import { ArrowRight, CheckCircle, Zap, Shield, Clock } from "lucide-react";

export default function Home() {
  return (
    <div className="w-full overflow-hidden">
      {/* Hero Section */}
      <section className="section-wrapper bg-gradient-to-br from-blue-50 to-white py-12 sm:py-16 md:py-24">
        <div className="section-inner">
          <div className="mobile-stack text-center">
            <h1 className="heading-responsive text-gray-900">
              AI-Powered Invoice Processing
            </h1>
            <p className="text-base sm:text-lg text-gray-600 max-w-2xl mx-auto">
              Streamline your orthodontic practice with intelligent invoice
              processing powered by artificial intelligence.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 justify-center pt-6 sm:pt-8">
              <Link
                href="/signup"
                className="button-mobile bg-blue-600 text-white hover:bg-blue-700"
              >
                Get Started Free
              </Link>
              <Link
                href="/demo"
                className="button-mobile border border-gray-300 text-gray-700 hover:bg-gray-50"
              >
                Watch Demo
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="section-wrapper py-12 sm:py-16 md:py-24">
        <div className="section-inner">
          <h2 className="heading-responsive text-center text-gray-900 mb-8 sm:mb-12 md:mb-16">
            Why Choose OrthoFlow AI?
          </h2>

          <div className="mobile-grid">
            {/* Feature Card 1 */}
            <div className="card-mobile">
              <div className="flex gap-3 sm:gap-4">
                <div className="flex-shrink-0">
                  <Zap className="w-6 h-6 sm:w-8 sm:h-8 text-blue-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-gray-900 text-base sm:text-lg">
                    Lightning Fast
                  </h3>
                  <p className="text-sm text-gray-600 mt-2">
                    Process invoices in seconds, not hours.
                  </p>
                </div>
              </div>
            </div>

            {/* Feature Card 2 */}
            <div className="card-mobile">
              <div className="flex gap-3 sm:gap-4">
                <div className="flex-shrink-0">
                  <Shield className="w-6 h-6 sm:w-8 sm:h-8 text-blue-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-gray-900 text-base sm:text-lg">
                    Secure & Compliant
                  </h3>
                  <p className="text-sm text-gray-600 mt-2">
                    HIPAA-compliant data handling.
                  </p>
                </div>
              </div>
            </div>

            {/* Feature Card 3 */}
            <div className="card-mobile">
              <div className="flex gap-3 sm:gap-4">
                <div className="flex-shrink-0">
                  <Clock className="w-6 h-6 sm:w-8 sm:h-8 text-blue-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-gray-900 text-base sm:text-lg">
                    24/7 Available
                  </h3>
                  <p className="text-sm text-gray-600 mt-2">
                    Process anytime, anywhere.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Benefits Section */}
      <section className="section-wrapper bg-gray-50 py-12 sm:py-16 md:py-24">
        <div className="section-inner">
          <h2 className="heading-responsive text-center text-gray-900 mb-8 sm:mb-12 md:mb-16">
            Key Benefits
          </h2>

          <div className="mobile-stack max-w-3xl mx-auto">
            {[
              "Reduce manual data entry by 95%",
              "Improve accuracy with AI validation",
              "Cut processing time from hours to minutes",
              "Integrate seamlessly with your existing systems",
            ].map((benefit, idx) => (
              <div key={idx} className="flex gap-3 sm:gap-4">
                <CheckCircle className="w-5 h-5 sm:w-6 sm:h-6 text-green-600 flex-shrink-0 mt-0.5" />
                <p className="text-base sm:text-lg text-gray-700">{benefit}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="section-wrapper bg-blue-600 py-12 sm:py-16 md:py-20">
        <div className="section-inner text-center">
          <h2 className="heading-responsive text-white mb-4 sm:mb-6">
            Ready to Transform Your Workflow?
          </h2>
          <p className="text-base sm:text-lg text-blue-100 mb-8 max-w-2xl mx-auto">
            Join orthodontists nationwide using OrthoFlow AI to save time and
            reduce errors.
          </p>
          <Link
            href="/signup"
            className="inline-flex items-center gap-2 button-mobile bg-white text-blue-600 hover:bg-gray-100 font-semibold"
          >
            Start Your Free Trial <ArrowRight size={20} />
          </Link>
        </div>
      </section>
    </div>
  );
}