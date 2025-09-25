import { useEffect, useState } from "react";
import { API_BASE_URL } from "./config";
import "./App.css";

type Row = {
  symbol: string;
  last: number;
  chg: number;
  d1: number;
  d7: number;
};

function App() {
  const [rows, setRows] = useState<Row[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE_URL}/markets/summary`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data: Row[]) => setRows(data))
      .catch((e) => setError(e.message));
  }, []);

  return (
    <main className="container" style={{ padding: 24, fontFamily: "Inter, system-ui, sans-serif" }}>
      <h1 style={{ marginBottom: 12 }}>EquiNova Desktop</h1>

      {error && <p>Backend error: {error}</p>}
      {!rows && !error && <p>Loading…</p>}

      {rows && (
        <table style={{ borderCollapse: "collapse", width: "100%", maxWidth: 720 }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: "8px" }}>Symbol</th>
              <th style={{ textAlign: "right", borderBottom: "1px solid #ddd", padding: "8px" }}>Last</th>
              <th style={{ textAlign: "right", borderBottom: "1px solid #ddd", padding: "8px" }}>Chg</th>
              <th style={{ textAlign: "right", borderBottom: "1px solid #ddd", padding: "8px" }}>1D%</th>
              <th style={{ textAlign: "right", borderBottom: "1px solid #ddd", padding: "8px" }}>7D%</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.symbol}>
                <td style={{ padding: "8px" }}>{r.symbol}</td>
                <td style={{ padding: "8px", textAlign: "right" }}>{r.last.toLocaleString()}</td>
                <td style={{ padding: "8px", textAlign: "right" }}>{r.chg.toLocaleString()}</td>
                <td style={{ padding: "8px", textAlign: "right" }}>{r.d1.toFixed(2)}%</td>
                <td style={{ padding: "8px", textAlign: "right" }}>{r.d7.toFixed(2)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}

export default App;