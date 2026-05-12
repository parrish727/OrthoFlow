import Link from "next/link";

export default function Footer() {
  return (
    <footer className="bg-gray-900 text-gray-300 mt-12 sm:mt-16 md:mt-20">
      <div className="section-wrapper">
        <div className="section-inner py-8 sm:py-12 md:py-16">
          <div className="mobile-grid md:grid-cols-4">
            <div className="mobile-stack">
              <h3 className="font-bold text-white text-lg">OrthoFlow AI</h3>
              <p className="text-sm">
                AI-powered invoice processing for orthodontists.
              </p>
            </div>

            <div className="mobile-stack">
              <h4 className="font-semibold text-white">Product</h4>
              <Link href="/features" className="text-sm hover:text-white">
                Features
              </Link>
              <Link href="/pricing" className="text-sm hover:text-white">
                Pricing
              </Link>
            </div>

            <div className="mobile-stack">
              <h4 className="font-semibold text-white">Company</h4>
              <Link href="/about" className="text-sm hover:text-white">
                About
              </Link>
              <Link href="/contact" className="text-sm hover:text-white">
                Contact
              </Link>
            </div>

            <div className="mobile-stack">
              <h4 className="font-semibold text-white">Legal</h4>
              <Link href="/privacy" className="text-sm hover:text-white">
                Privacy
              </Link>
              <Link href="/terms" className="text-sm hover:text-white">
                Terms
              </Link>
            </div>
          </div>

          <div className="border-t border-gray-700 mt-8 sm:mt-12 pt-8 sm:pt-12 text-center text-sm">
            <p>© 2024 OrthoFlow AI. All rights reserved.</p>
          </div>
        </div>
      </div>
    </footer>
  );
}