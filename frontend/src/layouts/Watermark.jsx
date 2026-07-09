import brandMark from "../assets/image/brand-mark.png";

/** Faint Darbha Prana brand mark, fixed behind the page content. */
function Watermark() {
  return <img src={brandMark} alt="" aria-hidden="true" className="brand-watermark" />;
}

export default Watermark;
