import Link from 'next/link';

type BrandProps = { className?: string };

export default function Brand({ className = '' }: BrandProps) {
  return (
    <Link href="/" className={`brand ${className}`} aria-label="MadhuMitra home">
      <img className="brand-logo" src="/madhumitra-logo.png" alt="" />
      <strong>MadhuMitra<small>CONNECTED DIABETES CARE</small></strong>
    </Link>
  );
}
