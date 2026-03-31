export function AnimatedBackground() {
  return (
    <>
      <div className="pointer-events-none fixed inset-0 -z-20 bg-app-grid" />
      <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
        <div className="orb orb-primary" />
        <div className="orb orb-secondary" />
        <div className="orb orb-accent" />
      </div>
    </>
  );
}
