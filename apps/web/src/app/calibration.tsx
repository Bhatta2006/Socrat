'use client';

import { useEffect, useState } from 'react';

type Cell = { track: string; language: string; started: number; completed: number; limited: number;
  pending_review: number; synthetic: boolean; outcome_pairs: number; calibration: string; brier_score: number | null };
type Calibration = { items: Cell[]; evidence_events: number; excluded_events: number; note: string };

export default function CalibrationPanel() {
  const [data, setData] = useState<Calibration | null>(null);
  useEffect(() => {
    let active = true;
    fetch('/api/v1/admin/diagnostics/calibration', { credentials: 'same-origin' }).then(async response => {
      if (response.ok && active) setData(await response.json());
    }).catch(() => {});
    return () => { active = false; };
  }, []);
  if (!data) return null;
  return <section className="card card-border" aria-label="Diagnostic calibration">
    <div className="card-body">
      <h2 className="card-title">Diagnostic calibration</h2>
      <p>{data.note}</p>
      <p>{data.evidence_events} evidence events; {data.excluded_events} excluded from scoring.</p>
      <div className="overflow-x-auto">
        <table className="table">
          <caption className="text-left">Track and language cohorts. Test cohorts are labeled synthetic.</caption>
          <thead><tr><th scope="col">Cohort</th><th scope="col">Started</th><th scope="col">Placed</th>
            <th scope="col">Limited</th><th scope="col">Pending review</th><th scope="col">Calibration</th></tr></thead>
          <tbody>{data.items.map(cell => <tr key={`${cell.track}:${cell.language}`}>
            <th scope="row">{cell.track} / {cell.language}{cell.synthetic ? ' (synthetic)' : ''}</th>
            <td>{cell.started}</td><td>{cell.completed}</td><td>{cell.limited}</td><td>{cell.pending_review}</td>
            <td>{cell.calibration === 'insufficient_data' ? 'Insufficient independent outcomes'
              : `${cell.outcome_pairs} outcome pairs; Brier score ${cell.brier_score?.toFixed(3)}`}</td>
          </tr>)}</tbody>
        </table>
      </div>
      {data.items.length === 0 && <p>No diagnostic cohorts yet.</p>}
    </div>
  </section>;
}
