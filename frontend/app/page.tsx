import ConverterWorkbench from "../components/converter-workbench";
import { JsonLd } from "../components/json-ld";
import { SITE_DESCRIPTION, SITE_NAME, SITE_URL } from "../lib/site";

const faqs = [
  {
    question: "How do I convert images to PDF online?",
    answer:
      "Choose your JPG, PNG, JPEG, WebP, TIFF, BMP, or GIF images, arrange them in the order you want, select your PDF settings, and choose Convert images to PDF. Your browser downloads the finished PDF when it is ready.",
  },
  {
    question: "Can I convert multiple images into one PDF?",
    answer:
      "Yes. Add multiple images, move them into the right order with the up and down controls, and create one multi-page PDF document.",
  },
  {
    question: "Is this image to PDF converter free?",
    answer:
      "Yes. You can create PDFs without an account or signup. The tool provides optional page size, orientation, margin, DPI, and quality settings before you download your file.",
  },
  {
    question: "Which image formats can I convert to PDF?",
    answer:
      "The converter supports JPG and JPEG photos, PNG, WebP, TIFF, BMP, and GIF image files. For the broadest compatibility, JPG, JPEG, and PNG are ideal choices.",
  },
  {
    question: "Are my uploaded images private?",
    answer:
      "Images are used to create your requested PDF in a temporary processing area. The service removes temporary upload files after the conversion request completes.",
  },
  {
    question: "Will converting images to PDF crop my photos?",
    answer:
      "No. The converter fits each image within the page and keeps its proportions. You can choose A4, Letter, or original image proportions and set the page margin.",
  },
];

const structuredData = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "WebSite",
      "@id": `${SITE_URL}/#website`,
      name: SITE_NAME,
      url: SITE_URL,
      description: SITE_DESCRIPTION,
      inLanguage: "en",
    },
    {
      "@type": "Organization",
      "@id": `${SITE_URL}/#organization`,
      name: SITE_NAME,
      url: SITE_URL,
      logo: `${SITE_URL}/favicon.svg`,
    },
    {
      "@type": "WebApplication",
      "@id": `${SITE_URL}/#webapplication`,
      name: SITE_NAME,
      url: SITE_URL,
      description: SITE_DESCRIPTION,
      applicationCategory: "UtilitiesApplication",
      operatingSystem: "Any",
      browserRequirements: "Requires JavaScript and a modern web browser.",
      isAccessibleForFree: true,
      offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
      featureList: [
        "Convert JPG, JPEG, PNG, WebP, TIFF, BMP, and GIF images to PDF",
        "Merge multiple images into one PDF document",
        "Reorder pages before converting",
        "Choose A4, Letter, or original image page format",
        "Set orientation, margin, DPI, and image quality",
      ],
      publisher: { "@id": `${SITE_URL}/#organization` },
    },
    {
      "@type": "SoftwareApplication",
      "@id": `${SITE_URL}/#softwareapplication`,
      name: SITE_NAME,
      applicationCategory: "UtilitiesApplication",
      operatingSystem: "Web",
      url: SITE_URL,
      description: SITE_DESCRIPTION,
      offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
    },
    {
      "@type": "BreadcrumbList",
      itemListElement: [
        {
          "@type": "ListItem",
          position: 1,
          name: "Image to PDF Converter",
          item: SITE_URL,
        },
      ],
    },
    {
      "@type": "FAQPage",
      mainEntity: faqs.map(({ question, answer }) => ({
        "@type": "Question",
        name: question,
        acceptedAnswer: { "@type": "Answer", text: answer },
      })),
    },
  ],
};

export default function Home() {
  return (
    <main className="site-shell" id="top">
      <JsonLd data={structuredData} />
      <div className="aurora aurora-one" />
      <div className="aurora aurora-two" />

      <header className="topbar">
        <a className="brand" href="#top" aria-label="Image to PDF Converter home"><span className="brand-mark">i</span>image<span>to PDF</span></a>
        <nav className="site-nav" aria-label="Main navigation">
          <a href="#how-it-works">How it works</a>
          <a href="#features">Features</a>
          <a href="#faq">FAQ</a>
        </nav>
        <a className="nav-cta" href="#converter">Convert images</a>
      </header>

      <section className="hero" aria-labelledby="page-title">
        <p className="eyebrow"><span /> Free online tool · No signup</p>
        <h1 id="page-title">Image to PDF <em>Converter</em></h1>
        <p className="hero-copy">Convert JPG, PNG, JPEG, and other image files into one high-quality PDF online. Arrange multiple images, set the layout, and download your PDF in a few simple steps.</p>
        <div className="hero-actions">
          <a className="button button-dark" href="#converter">Convert images to PDF <span aria-hidden="true">↓</span></a>
          <a className="quiet-link" href="#how-it-works">See how it works <span aria-hidden="true">→</span></a>
        </div>
        <ul className="hero-meta" aria-label="Converter benefits">
          <li>JPG · JPEG · PNG · WebP</li>
          <li>Multiple images in one PDF</li>
          <li>Temporary file processing</li>
        </ul>
      </section>

      <ConverterWorkbench />

      <section className="content-intro" aria-labelledby="online-converter-title">
        <p className="section-kicker">A practical document tool</p>
        <h2 id="online-converter-title">A free image to PDF converter for everyday documents</h2>
        <p>Use this online image to PDF converter when you need to turn scans, photos, receipts, homework, reports, or forms into one shareable document. It is designed for quick conversions on desktop and mobile without a registration step.</p>
      </section>

      <section className="feature-section" id="features" aria-labelledby="features-title">
        <div className="section-heading"><p className="section-kicker">What you can do</p><h2 id="features-title">Built for more than a single photo</h2></div>
        <div className="feature-grid">
          <article><span className="feature-number">01</span><h3>Merge images into one PDF</h3><p>Add several pictures or scanned pages, arrange the order, and create one neat multi-page document.</p></article>
          <article><span className="feature-number">02</span><h3>Choose the right page layout</h3><p>Pick A4, Letter, or original image proportions, then control the page orientation and margins.</p></article>
          <article><span className="feature-number">03</span><h3>Keep your document readable</h3><p>Select output DPI and quality settings to make PDFs suitable for sharing, printing, or archiving.</p></article>
          <article><span className="feature-number">04</span><h3>Convert from any device</h3><p>The mobile-friendly interface lets you make a photo to PDF document from a phone, tablet, or computer.</p></article>
        </div>
      </section>

      <section className="how-section" id="how-it-works" aria-labelledby="how-title">
        <div className="section-heading"><p className="section-kicker">How it works</p><h2 id="how-title">Convert multiple images to PDF in three steps</h2></div>
        <ol className="steps-list">
          <li><span>1</span><div><h3>Upload your images</h3><p>Choose JPG, PNG, JPEG, or another supported image format from your device.</p></div></li>
          <li><span>2</span><div><h3>Arrange and adjust</h3><p>Put pages in order, then choose your paper size, orientation, margins, and quality.</p></div></li>
          <li><span>3</span><div><h3>Download your PDF</h3><p>Create one PDF and save it directly to your device when the conversion is complete.</p></div></li>
        </ol>
      </section>

      <section className="security-section" aria-labelledby="privacy-title">
        <div><p className="section-kicker">Privacy by design</p><h2 id="privacy-title">Simple file conversion, with a lighter footprint</h2></div>
        <div><p>Your uploaded images are used only to create the PDF you request. The conversion service processes files in a temporary area and removes those temporary uploads after the request completes.</p><p>No account is needed to use the tool, and there are no unnecessary steps between uploading your images and downloading your PDF.</p></div>
      </section>

      <section className="formats-section" aria-labelledby="formats-title">
        <p className="section-kicker">Supported formats</p>
        <h2 id="formats-title">Convert common image files into a PDF</h2>
        <p>Upload JPG or JPEG photos, PNG screenshots, WebP images, TIFF scans, BMP files, or GIF images. For most documents, JPG, JPEG, and PNG provide the best mix of quality and compatibility.</p>
        <a className="text-link" href="#converter">Start a free image to PDF conversion <span aria-hidden="true">→</span></a>
      </section>

      <section className="faq-section" id="faq" aria-labelledby="faq-title">
        <div className="section-heading"><p className="section-kicker">Helpful answers</p><h2 id="faq-title">Image to PDF converter FAQ</h2></div>
        <div className="faq-list">
          {faqs.map(({ question, answer }) => <details key={question}><summary>{question}</summary><p>{answer}</p></details>)}
        </div>
      </section>

      <footer>
        <span>{SITE_NAME}</span>
        <nav aria-label="Footer navigation"><a href="#converter">Convert images</a><a href="#how-it-works">How it works</a><a href="#faq">FAQ</a></nav>
        <p>Free, simple image to PDF conversion.</p>
      </footer>
    </main>
  );
}
