import React from "react";
import { ValidationSummary } from "@/lib/api-client";
import { AlertCircle, CheckCircle2, Info } from "lucide-react";

interface ValidationDashboardProps {
  report: ValidationSummary;
}

function RealismScoreRing({ score }: { score: number | null }) {
  if (score === null) return null;
  const radius = 36;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color = score >= 85 ? "#22c55e" : score >= 60 ? "#eab308" : "#ef4444";
  return (
    <svg width="88" height="88" viewBox="0 0 88 88" className="shrink-0">
      <circle cx="44" cy="44" r={radius} fill="none" stroke="currentColor" className="text-muted" strokeWidth="8" />
      <circle
        cx="44" cy="44" r={radius} fill="none"
        stroke={color} strokeWidth="8"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        transform="rotate(-90 44 44)"
        style={{ transition: "stroke-dashoffset 0.8s ease" }}
      />
      <text x="44" y="48" textAnchor="middle" fontSize="18" fontWeight="bold" fill={color}>
        {Math.round(score)}
      </text>
    </svg>
  );
}

function ConfidenceBadge({ level }: { level: string }) {
  const styles = {
    high: "bg-green-100 text-green-800 border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-800",
    medium: "bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-400 dark:border-yellow-800",
    low: "bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800",
    unknown: "bg-gray-100 text-gray-800 border-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:border-gray-700"
  };
  const colorClass = styles[level as keyof typeof styles] || styles.unknown;
  return (
    <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${colorClass} uppercase tracking-wider`}>
      {level} CONFIDENCE
    </span>
  );
}

export function ValidationDashboard({ report }: ValidationDashboardProps) {
  if (!report || report.realism_score === null) {
    return (
      <div className="flex items-center gap-3 p-4 border rounded-lg bg-card text-muted-foreground text-sm">
        <Info className="h-5 w-5" />
        Validation report not available for this generation.
      </div>
    );
  }

  return (
    <div className="space-y-6 mt-8">
      {/* 1. HEADER STRIP */}
      <div className="flex items-center gap-4 p-5 border rounded-xl bg-card shadow-sm">
        <RealismScoreRing score={report.realism_score} />
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-bold text-foreground">Statistical Validation</h3>
            <ConfidenceBadge level={report.confidence} />
          </div>
          <span className="text-sm text-muted-foreground flex items-center gap-1.5">
            {report.passed ? (
              <><CheckCircle2 className="h-4 w-4 text-green-500" /> Dataset passed statistical fidelity checks</>
            ) : (
              <><AlertCircle className="h-4 w-4 text-red-500" /> Issues detected in dataset distribution</>
            )}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 2. DISTRIBUTION COMPARISON CHART (KS TESTS) */}
        {report.ks_tests && Object.keys(report.ks_tests).length > 0 && (
          <div className="border rounded-xl bg-card p-5 shadow-sm">
            <h4 className="text-sm font-bold text-foreground mb-4">Numeric Fidelity (KS Tests)</h4>
            <div className="space-y-3">
              {Object.entries(report.ks_tests).map(([col, data]: [string, any]) => {
                const pValue = data.p_value;
                const passed = data.passed;
                return (
                  <div key={col} className="flex flex-col gap-1">
                    <div className="flex justify-between text-xs">
                      <span className="font-medium">{col}</span>
                      <span className={passed ? "text-green-600" : "text-red-500"}>p = {pValue.toFixed(3)}</span>
                    </div>
                    <div className="h-2 w-full bg-muted rounded-full overflow-hidden relative">
                      {/* Threshold line at 0.05 */}
                      <div className="absolute top-0 bottom-0 left-[5%] w-[1px] bg-red-500/50 z-10" />
                      <div
                        className={`h-full ${passed ? 'bg-green-500' : 'bg-red-500'}`}
                        style={{ width: `${Math.min(pValue * 100, 100)}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* 3. CATEGORICAL FIDELITY TABLE */}
        {report.kl_divergence && Object.keys(report.kl_divergence).length > 0 && (
          <div className="border rounded-xl bg-card p-5 shadow-sm">
            <h4 className="text-sm font-bold text-foreground mb-4">Categorical Fidelity (KL Div)</h4>
            <div className="overflow-hidden rounded-md border text-sm">
              <table className="w-full text-left">
                <thead className="bg-muted/50 text-muted-foreground border-b">
                  <tr>
                    <th className="p-2 font-medium">Column</th>
                    <th className="p-2 font-medium">KL Div</th>
                    <th className="p-2 font-medium text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {Object.entries(report.kl_divergence).map(([col, data]: [string, any]) => (
                    <tr key={col}>
                      <td className="p-2 font-medium">{col}</td>
                      <td className="p-2">{data.kl_div.toFixed(3)}</td>
                      <td className="p-2 text-center">
                        {data.passed ? <span className="text-green-500">Pass</span> : <span className="text-red-500">Fail</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* 4. CORRELATION HEATMAP DATA */}
      {report.correlation_error && (
        <div className="border rounded-xl bg-card p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-sm font-bold text-foreground">Correlation Matrix Drift</h4>
            <div className="text-xs px-2 py-1 bg-muted rounded-md font-mono">
              Frobenius Norm: {report.correlation_error.frobenius_norm?.toFixed(3) || "N/A"}
            </div>
          </div>
          <div className="flex gap-4 text-sm">
            <div className="bg-muted/30 p-3 rounded flex-1">
              <div className="text-muted-foreground text-xs uppercase mb-1">Max Error</div>
              <div className="font-bold">{report.correlation_error.max_pair_error?.toFixed(3) || "N/A"}</div>
            </div>
            <div className="bg-muted/30 p-3 rounded flex-1">
              <div className="text-muted-foreground text-xs uppercase mb-1">Divergent Pairs</div>
              <div className="font-bold">{report.correlation_error.pairs_above_threshold}</div>
            </div>
            <div className="bg-muted/30 p-3 rounded flex-1">
              <div className="text-muted-foreground text-xs uppercase mb-1">Status</div>
              <div className={`font-bold ${report.correlation_error.passed ? "text-green-500" : "text-red-500"}`}>
                {report.correlation_error.passed ? "Preserved" : "Distorted"}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 5. WARNINGS LIST */}
      {report.warnings && report.warnings.length > 0 && (
        <div className="border rounded-xl border-red-200 bg-red-50/50 p-5 dark:bg-red-950/10 dark:border-red-900/50 shadow-sm">
          <h4 className="text-sm font-bold text-red-800 dark:text-red-400 mb-3 flex items-center gap-2">
            <AlertCircle className="h-4 w-4" /> Validation Alerts
          </h4>
          <ul className="space-y-2 text-sm text-red-700 dark:text-red-300">
            {report.warnings.map((w, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="mt-0.5">•</span>
                <span>{w.column ? <strong>{w.column}: </strong> : null}{w.message}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
