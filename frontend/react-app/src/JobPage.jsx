import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button.jsx'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card.jsx'
import { Progress } from '@/components/ui/progress.jsx'
import { Badge } from '@/components/ui/badge.jsx'
import { Alert, AlertDescription } from '@/components/ui/alert.jsx'
import { ArrowLeft, RefreshCw, Download, ExternalLink, CheckCircle, XCircle, Clock, Loader2 } from 'lucide-react'

function JobPage() {
  const { jobId } = useParams()
  const navigate = useNavigate()
  const [jobData, setJobData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [results, setResults] = useState(null)
  const [autoRefresh, setAutoRefresh] = useState(true)

  useEffect(() => {
    if (!jobId) {
      setError('No job ID provided')
      setLoading(false)
      return
    }

    fetchJobStatus()
  }, [jobId])

  useEffect(() => {
    let interval
    if (autoRefresh && jobData && ['pending', 'running'].includes(jobData.status)) {
      interval = setInterval(fetchJobStatus, 2000) // Poll every 2 seconds
    }
    return () => {
      if (interval) clearInterval(interval)
    }
  }, [autoRefresh, jobData])

  const fetchJobStatus = async () => {
    try {
      const response = await fetch(`/api/gitsnip/status/${jobId}`)
      
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Job not found')
        }
        throw new Error('Failed to fetch job status')
      }

      const data = await response.json()
      setJobData(data)
      
      // If job is completed, fetch results
      if (data.status === 'completed' && !results) {
        fetchJobResults()
      }
      
      // Stop auto-refresh if job is completed or failed
      if (['completed', 'failed'].includes(data.status)) {
        setAutoRefresh(false)
      }
      
      setLoading(false)
    } catch (err) {
      console.error('Error fetching job status:', err)
      setError(err.message)
      setLoading(false)
      setAutoRefresh(false)
    }
  }

  const fetchJobResults = async () => {
    try {
      const response = await fetch(`/api/gitsnip/results/${jobId}`)
      
      if (response.ok) {
        const data = await response.json()
        setResults(data.results)
      }
    } catch (err) {
      console.error('Error fetching results:', err)
    }
  }

  const formatAnalysisResults = (resultsData) => {
    if (!resultsData) return 'No results available'
    
    let formatted = `# GitSnip Analysis Results\n\n`
    formatted += `**Repository:** ${resultsData.repository_url || 'Unknown'}\n`
    formatted += `**Analysis Mode:** ${resultsData.analysis_mode || 'Unknown'}\n\n`
    
    if (resultsData.analysis_summary) {
      formatted += `## Summary\n${resultsData.analysis_summary}\n\n`
    }
    
    if (resultsData.files_analyzed) {
      formatted += `## Files Analyzed\n`
      resultsData.files_analyzed.forEach(file => {
        formatted += `- ${file}\n`
      })
      formatted += '\n'
    }
    
    return formatted
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />
      case 'running':
        return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />
      default:
        return <Clock className="h-5 w-5 text-yellow-500" />
    }
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800'
      case 'failed':
        return 'bg-red-100 text-red-800'
      case 'running':
        return 'bg-blue-100 text-blue-800'
      default:
        return 'bg-yellow-100 text-yellow-800'
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <Card className="w-full max-w-md">
          <CardContent className="flex items-center justify-center p-8">
            <Loader2 className="h-8 w-8 animate-spin mr-3" />
            <span>Loading job details...</span>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="flex items-center text-red-600">
              <XCircle className="h-6 w-6 mr-2" />
              Error
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Alert>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
            <div className="mt-4 flex gap-2">
              <Button onClick={() => navigate('/')} variant="outline">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Home
              </Button>
              <Button onClick={() => window.location.reload()}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Retry
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <Button 
            onClick={() => navigate('/')} 
            variant="outline" 
            className="mb-4"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Home
          </Button>
          
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Analysis Job: {jobId}
          </h1>
          
          <div className="flex items-center gap-4">
            <Badge className={getStatusColor(jobData?.status)}>
              {getStatusIcon(jobData?.status)}
              <span className="ml-2 capitalize">{jobData?.status}</span>
            </Badge>
            
            {jobData?.analysis_mode && (
              <Badge variant="outline">
                {jobData.analysis_mode === 'fast' ? '⚡ Fast Analysis' : '🔍 Detailed Analysis'}
              </Badge>
            )}
          </div>
        </div>

        {/* Job Details */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Job Details</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-gray-500">Repository</label>
                <div className="flex items-center mt-1">
                  <span className="text-sm">{jobData?.repository_url}</span>
                  {jobData?.repository_url && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => window.open(jobData.repository_url, '_blank')}
                      className="ml-2 p-1"
                    >
                      <ExternalLink className="h-3 w-3" />
                    </Button>
                  )}
                </div>
              </div>
              
              <div>
                <label className="text-sm font-medium text-gray-500">Created</label>
                <p className="text-sm mt-1">
                  {jobData?.created_at ? new Date(jobData.created_at).toLocaleString() : 'Unknown'}
                </p>
              </div>
              
              <div>
                <label className="text-sm font-medium text-gray-500">Last Updated</label>
                <p className="text-sm mt-1">
                  {jobData?.updated_at ? new Date(jobData.updated_at).toLocaleString() : 'Unknown'}
                </p>
              </div>
              
              <div>
                <label className="text-sm font-medium text-gray-500">Analysis Mode</label>
                <p className="text-sm mt-1 capitalize">
                  {jobData?.analysis_mode || 'Unknown'}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Progress */}
        {jobData && ['pending', 'running'].includes(jobData.status) && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Progress</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <Progress value={jobData.progress || 0} className="w-full" />
                <div className="flex justify-between text-sm text-gray-600">
                  <span>{jobData.message || 'Processing...'}</span>
                  <span>{jobData.progress || 0}%</span>
                </div>
                
                {autoRefresh && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-500 flex items-center">
                      <Loader2 className="h-3 w-3 animate-spin mr-1" />
                      Auto-refreshing every 2 seconds
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setAutoRefresh(false)}
                    >
                      Stop Auto-refresh
                    </Button>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Error Display */}
        {jobData?.status === 'failed' && (
          <Card className="mb-6 border-red-200">
            <CardHeader>
              <CardTitle className="text-red-600">Analysis Failed</CardTitle>
            </CardHeader>
            <CardContent>
              <Alert>
                <XCircle className="h-4 w-4" />
                <AlertDescription>
                  {jobData.error || jobData.message || 'Unknown error occurred'}
                </AlertDescription>
              </Alert>
              
              <div className="mt-4">
                <Button onClick={() => navigate('/')} variant="outline">
                  Start New Analysis
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Results */}
        {jobData?.status === 'completed' && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Analysis Results</span>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={fetchJobResults}
                  >
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Refresh
                  </Button>
                  {results && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        const blob = new Blob([formatAnalysisResults(results)], { type: 'text/markdown' })
                        const url = URL.createObjectURL(blob)
                        const a = document.createElement('a')
                        a.href = url
                        a.download = `gitsnip-analysis-${jobId}.md`
                        a.click()
                        URL.revokeObjectURL(url)
                      }}
                    >
                      <Download className="h-4 w-4 mr-2" />
                      Download
                    </Button>
                  )}
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {results ? (
                <div className="bg-gray-50 p-4 rounded-lg">
                  <pre className="whitespace-pre-wrap text-sm">
                    {formatAnalysisResults(results)}
                  </pre>
                </div>
              ) : (
                <div className="text-center py-8">
                  <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
                  <p className="text-gray-500">Loading results...</p>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Manual Refresh */}
        {!autoRefresh && ['pending', 'running'].includes(jobData?.status) && (
          <div className="mt-6 text-center">
            <Button onClick={fetchJobStatus} variant="outline">
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh Status
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}

export default JobPage

