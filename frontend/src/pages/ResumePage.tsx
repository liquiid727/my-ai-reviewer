import { useParams } from 'react-router'

export function ResumePage() {
  const { id } = useParams()
  return (
    <div>
      <h1 className="text-3xl font-black">Resume Result</h1>
      <p className="mt-2 text-gray-600">Resume ID: {id}</p>
    </div>
  )
}
