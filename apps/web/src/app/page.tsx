import Workspace from './workspace';

export default function Home() {
  return (
    <main className="min-h-screen bg-base-100 text-base-content">
      <a className="sr-only focus:not-sr-only focus:absolute focus:m-4 focus:bg-base-100 focus:p-3" href="#workspace">
        Skip to workspace
      </a>
      <div className="mx-auto flex min-h-screen w-full max-w-5xl flex-col px-5 py-6 sm:px-8 sm:py-10">
        <header className="flex items-center justify-between border-b border-base-300 pb-5">
          <span className="text-lg font-bold tracking-tight">SOCRAT</span>
          <span className="text-xs uppercase tracking-[0.18em] text-base-content/60">Learning workspace</span>
        </header>

        <section className="grid flex-1 items-center gap-12 py-14 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="max-w-xl">
            <p className="mb-4 text-sm font-semibold uppercase tracking-[0.16em]">DSA first. More skills next.</p>
            <h1 className="text-5xl font-bold leading-[0.95] tracking-[-0.055em] sm:text-7xl">
              A foundation for your learning.
            </h1>
            <p className="mt-7 max-w-lg text-lg leading-8 text-base-content/70">
              Socrat is building personalized DSA preparation for beginners, interview learners, and competitive
              programmers in Python, C++, and Java.
            </p>
          </div>

          <Workspace />
        </section>

        <footer className="border-t border-base-300 pt-5 text-sm text-base-content/60">
          Choose and confirm your learning goal when onboarding is available. Learning sessions are not enabled yet.
        </footer>
      </div>
    </main>
  );
}
