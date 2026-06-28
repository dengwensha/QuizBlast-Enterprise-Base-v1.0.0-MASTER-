export default function QBCard({ children, className = "" }) {
  return (
    <div className={`qb-card ${className}`}>
      {children}
    </div>
  );
}