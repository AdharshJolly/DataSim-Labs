"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"

export default function ProfileUploadPage() {
  const router = useRouter()
  const [file, setFile] = useState<File | null>(null)
  const [datasetVersionId, setDatasetVersionId] = useState("")
  const [profile, setProfile] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0])
    }
  }

  const handleUpload = async () => {
    if (!file || !datasetVersionId) {
      setError("Please provide both a file and a Dataset Version ID.")
      return
    }

    setLoading(true)
    setError("")

    const formData = new FormData()
    formData.append("file", file)

    try {
      const response = await fetch(`/api/dataset/${datasetVersionId}/profile/upload`, {
        method: "POST",
        body: formData,
        headers: {
          "Authorization": `Bearer ${localStorage.getItem("token") || ""}`
        }
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || "Failed to upload and profile dataset")
      }

      const data = await response.json()
      setProfile(data.profile)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container mx-auto p-8">
      <h1 className="text-3xl font-bold mb-6">Upload Real Dataset to Profile</h1>

      <div className="bg-white p-6 rounded-lg shadow-md mb-8">
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Dataset Version ID
          </label>
          <input
            type="text"
            value={datasetVersionId}
            onChange={(e) => setDatasetVersionId(e.target.value)}
            className="w-full p-2 border border-gray-300 rounded"
            placeholder="Enter UUID of Dataset Version"
          />
        </div>

        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Dataset File (CSV, JSON, Excel)
          </label>
          <input
            type="file"
            accept=".csv,.json,.xls,.xlsx"
            onChange={handleFileChange}
            className="w-full p-2 border border-gray-300 rounded"
          />
        </div>

        {error && <div className="text-red-500 mb-4">{error}</div>}

        <button
          onClick={handleUpload}
          disabled={loading}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "Profiling..." : "Upload & Profile"}
        </button>
      </div>

      {profile && (
        <div className="bg-white p-6 rounded-lg shadow-md">
          <h2 className="text-2xl font-bold mb-4">Profile Preview</h2>
          <div className="mb-4">
            <span className="font-semibold">Row Count:</span> {profile.row_count}
          </div>

          <h3 className="text-xl font-semibold mb-2 mt-6">Column Distributions</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(profile.columns).map(([colName, colData]: [string, any]) => (
              <div key={colName} className="border p-4 rounded bg-gray-50">
                <h4 className="font-bold text-lg">{colName}</h4>
                <p><span className="font-medium">Type:</span> {colData.data_type}</p>
                <p><span className="font-medium">Null Percentage:</span> {colData.null_percentage.toFixed(2)}%</p>
                {colData.distribution?.type && (
                  <p><span className="font-medium">Dist Type:</span> {colData.distribution.type}</p>
                )}
                {colData.data_type === "float" || colData.data_type === "integer" ? (
                  <div className="mt-2 text-sm text-gray-600">
                    <p>Mean: {colData.distribution?.mean?.toFixed(2)}</p>
                    <p>Min: {colData.distribution?.min}</p>
                    <p>Max: {colData.distribution?.max}</p>
                  </div>
                ) : null}
              </div>
            ))}
          </div>

          <h3 className="text-xl font-semibold mb-2 mt-8">Correlations & Dependencies</h3>
          {profile.dependency_graph && profile.dependency_graph.length > 0 ? (
            <div className="space-y-2">
              {profile.dependency_graph.map((dep: any, idx: number) => (
                <div key={idx} className="border p-3 rounded bg-blue-50 text-sm">
                  <span className="font-semibold">{dep.source} &rarr; {dep.target}</span>: {dep.type}
                  {dep.correlation && ` (Correlation: ${dep.correlation.toFixed(2)})`}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500">No strong correlations or dependencies detected.</p>
          )}
        </div>
      )}
    </div>
  )
}
