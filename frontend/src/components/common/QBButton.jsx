export default function QBButton({
  children,
  onClick,
  type = "button",
  variant = "primary",
  disabled = false,
}) {
  return (
    <button
      type={type}
      className={`qb-btn qb-btn-${variant}`}
      disabled={disabled}
      onClick={onClick}
    >
      {children}
    </button>
  );
}