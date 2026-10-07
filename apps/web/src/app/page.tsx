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

        <section className="flex flex-1 flex-col gap-8 py-8">
          <div className="max-w-xl">
            <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
              A foundation for your learning.
            </h1>
            <p className="mt-3 text-base leading-6">
              Your next step, independent learning evidence, and a plan that fits your day.
            </p>
          </div>

          <Workspace />
        </section>

        <footer className="border-t border-base-300 pt-5 text-sm text-base-content/60">
          Progress comes from demonstrated capability, with independent evidence and delayed retention checks.
        </footer>
      </div>
    </main>
  );
}
