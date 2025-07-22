import { useState } from 'react'
import { Button } from '@/components/ui/button.jsx'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card.jsx'
import { Input } from '@/components/ui/input.jsx'
import { Label } from '@/components/ui/label.jsx'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select.jsx'
import { Checkbox } from '@/components/ui/checkbox.jsx'
import { Progress } from '@/components/ui/progress.jsx'
import { Badge } from '@/components/ui/badge.jsx'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog.jsx'
import { Alert, AlertDescription } from '@/components/ui/alert.jsx'
import { Github, Settings, Key, Settings2, FileText, Download, Info, CheckCircle, XCircle, ArrowRight, ArrowLeft, Code, Loader2 } from 'lucide-react'
import './App.css'

function App() {
  const [currentStep, setCurrentStep] = useState(1)
  const [repoUrl, setRepoUrl] = useState('')
  const [isPrivateRepo, setIsPrivateRepo] = useState(false)
  const [analysisMode, setAnalysisMode] = useState('fast') // New: analysis mode
  const [userApiKey, setUserApiKey] = useState('') // New: user's Gemini API key
  const [includePatterns, setIncludePatterns] = useState(['*.py'])
  const [excludePatterns, setExcludePatterns] = useState([])
  const [maxFileSize, setMaxFileSize] = useState(100000)
  const [language, setLanguage] = useState('english')
  const [githubToken, setGithubToken] = useState('')
  const [currentPattern, setCurrentPattern] = useState('')
  const [currentExcludePattern, setCurrentExcludePattern] = useState('')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [progress, setProgress] = useState(0)
  const [analysisMessage, setAnalysisMessage] = useState('')
  const [jobId, setJobId] = useState('')
  const [results, setResults] = useState('')
  const [errors, setErrors] = useState({})
  const [showAbout, setShowAbout] = useState(false)

  const steps = [
    { id: 1, title: 'Repository', icon: Github },
    { id: 2, title: 'Configuration', icon: Settings },
    { id: 3, title: 'Authentication', icon: Key },
    { id: 4, title: 'Processing', icon: Settings2 },
    { id: 5, title: 'Results', icon: FileText }
  ]

  const validateRepoUrl = (url) => {
    if (!url) return 'Repository URL is required'
    if (!url.startsWith('https://github.com/')) return 'Only GitHub repositories are supported'
    const parts = url.replace('https://github.com/', '').split('/')
    if (parts.length < 2) return 'Invalid repository URL format'
    return null
  }

  const addPattern = (pattern, type) => {
    if (!pattern.trim()) return
    
    if (type === 'include') {
      if (!includePatterns.includes(pattern)) {
        setIncludePatterns([...includePatterns, pattern])
      }
      setCurrentPattern('')
    } else {
      if (!excludePatterns.includes(pattern)) {
        setExcludePatterns([...excludePatterns, pattern])
      }
      setCurrentExcludePattern('')
    }
  }

  const removePattern = (pattern, type) => {
    if (type === 'include') {
      setIncludePatterns(includePatterns.filter(p => p !== pattern))
    } else {
      setExcludePatterns(excludePatterns.filter(p => p !== pattern))
    }
  }

  const validateAndProceed = () => {
    const error = validateRepoUrl(repoUrl)
    if (error) {
      setErrors({ repoUrl: error })
      return
    }
    setErrors({})
    setCurrentStep(2)
  }

  const proceedToAuth = () => {
    // Validate analysis mode requirements
    if (analysisMode === 'detailed' && !userApiKey) {
      setErrors({ apiKey: 'Gemini API key is required for detailed analysis' })
      return
    }
    
    setErrors({})
    
    if (isPrivateRepo) {
      setCurrentStep(3)
    } else {
      startAnalysis()
    }
  }

  const validateTokenAndProceed = () => {
    if (!githubToken) {
      setErrors({ token: 'GitHub token is required for private repositories' })
      return
    }
    if (!githubToken.startsWith('ghp_') && !githubToken.startsWith('github_pat_')) {
      setErrors({ token: 'Invalid GitHub token format' })
      return
    }
    setErrors({})
    startAnalysis()
  }

  const startAnalysis = async () => {
    setCurrentStep(4)
    setIsAnalyzing(true)
    setProgress(0)
    setAnalysisMessage('Starting analysis...')

    try {
      // Prepare analysis request
      const analysisData = {
        repository_url: repoUrl,
        analysis_mode: analysisMode, // New: include analysis mode
        user_api_key: analysisMode === 'detailed' ? userApiKey : undefined, // New: include user API key for detailed mode
        config: {
          include_patterns: includePatterns,
          exclude_patterns: excludePatterns,
          max_file_size: maxFileSize,
          language: language,
          is_private: isPrivateRepo,
          github_token: isPrivateRepo ? githubToken : undefined
        }
      }

      // Start analysis
      setAnalysisMessage('Submitting analysis request...')
      const startResponse = await fetch('/api/gitsnip/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(analysisData)
      })

      if (!startResponse.ok) {
        const errorData = await startResponse.json()
        throw new Error(errorData.error || 'Failed to start analysis')
      }

      const responseData = await startResponse.json()
      const { job_id, redirect_url } = responseData
      setJobId(job_id)
      
      // Redirect to job page
      if (redirect_url) {
        window.location.href = redirect_url
        return
      }
      
      // Fallback: continue with polling in current page
      setProgress(5)
      setAnalysisMessage('Analysis started, monitoring progress...')
      pollJobProgress(job_id)

    } catch (error) {
      console.error('Error starting analysis:', error)
      setAnalysisMessage(`Error: ${error.message}`)
      setIsAnalyzing(false)
    }
  }

  const pollJobProgress = async (jobId) => {
    try {
      const statusResponse = await fetch(`/api/gitsnip/status/${jobId}`)
      
      if (!statusResponse.ok) {
        throw new Error('Failed to get analysis status')
      }

      const statusData = await statusResponse.json()
      setProgress(statusData.progress)
      setAnalysisMessage(statusData.message)

      if (statusData.status === 'completed') {
        // Get results
        const resultsResponse = await fetch(`/api/gitsnip/results/${jobId}`)
        
        if (resultsResponse.ok) {
          const resultsData = await resultsResponse.json()
          setResults(formatAnalysisResults(resultsData))
          setCurrentStep(5)
        } else {
          throw new Error('Failed to get analysis results')
        }
        
        setIsAnalyzing(false)
      } else if (statusData.status === 'failed') {
        throw new Error(statusData.message || 'Analysis failed')
      } else {
        // Continue polling
        setTimeout(() => pollJobProgress(jobId), 2000)
      }
    } catch (error) {
      console.error('Error polling progress:', error)
      setAnalysisMessage(`Error: ${error.message}`)
      setIsAnalyzing(false)
    }
  }
          setIsAnalyzing(false)
        }
      }

      // Start polling
      setTimeout(pollProgress, 1000)

    } catch (error) {
      console.error('Analysis error:', error)
      setAnalysisMessage(`Error: ${error.message}`)
      setIsAnalyzing(false)
    }
  }

  const formatAnalysisResults = (resultsData) => {
    const { results, repository_url } = resultsData
    
    if (!results) {
      return `# GitSnip Analysis Results\n\n## Repository: ${repository_url}\n\nAnalysis completed but no detailed results available.`
    }

    const summary = results.analysis_summary || {}
    
    return `# GitSnip Analysis Results

## Repository: ${repository_url}

### Project Structure
- **Project Name**: ${summary.project_name || 'Unknown'}
- **Files Analyzed**: ${summary.total_files || 'Unknown'} files
- **Generated Documentation**: ${summary.generated_files || 0} files
- **Analysis Date**: ${new Date(summary.analysis_date || Date.now()).toLocaleDateString()}

### Generated Documentation
${results.files && results.files.length > 0 ? 
  results.files.map(file => `- ${file}`).join('\n') : 
  'No documentation files generated'
}

### Analysis Summary
${summary.readme || 'Detailed analysis documentation has been generated and is available for download.'}

### Download Results
The complete analysis results including all generated documentation, diagrams, and tutorials are available for download.

### Next Steps
1. Download the complete analysis package
2. Review the generated documentation
3. Explore the project structure and relationships
4. Use the tutorials to understand the codebase

The analysis provides comprehensive insights into the codebase structure, key components, and their relationships to help you quickly understand and navigate the project.`
  }

  const decryptAndViewResults = async () => {
    if (!jobId || !isPrivateRepo || !githubToken) {
      alert('Missing required information for decryption')
      return
    }

    try {
      const response = await fetch(`/api/gitsnip/decrypt/${jobId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          github_token: githubToken
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Failed to decrypt results')
      }

      const decryptedData = await response.json()
      setResults(formatAnalysisResults(decryptedData))
    } catch (error) {
      console.error('Decryption error:', error)
      alert(`Failed to decrypt results: ${error.message}`)
    }
  }

  const downloadResults = async () => {
    if (!jobId) {
      alert('No analysis results available for download')
      return
    }

    try {
      if (isPrivateRepo) {
        // For private repos, send token with download request
        if (!githubToken) {
          alert('GitHub token is required for private repository download')
          return
        }

        const response = await fetch(`/api/gitsnip/download/${jobId}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            github_token: githubToken
          })
        })
        
        if (!response.ok) {
          const errorData = await response.json()
          throw new Error(errorData.error || 'Failed to download results')
        }

        // Handle blob download
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `gitsnip_analysis_${jobId}.zip`
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
      } else {
        // For public repos, normal GET request
        const response = await fetch(`/api/gitsnip/download/${jobId}`)
        
        if (!response.ok) {
          throw new Error('Failed to download results')
        }

        // Handle blob download
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `gitsnip_analysis_${jobId}.zip`
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
      }
    } catch (error) {
      console.error('Download error:', error)
      alert(`Download failed: ${error.message}`)
    }
  }

  const goToStep = (step) => {
    setCurrentStep(step)
  }

  const resetApp = () => {
    setCurrentStep(1)
    setRepoUrl('')
    setIsPrivateRepo(false)
    setAnalysisMode('fast') // Reset analysis mode
    setUserApiKey('') // Reset user API key
    setIncludePatterns(['*.py'])
    setExcludePatterns([])
    setMaxFileSize(100000)
    setLanguage('english')
    setGithubToken('')
    setCurrentPattern('')
    setCurrentExcludePattern('')
    setIsAnalyzing(false)
    setProgress(0)
    setAnalysisMessage('')
    setJobId('')
    setResults('')
    setErrors({})
  }

  const StepIndicator = () => (
    <div className="flex justify-center items-center space-x-4 mb-8">
      {steps.map((step, index) => {
        const Icon = step.icon
        const isActive = currentStep === step.id
        const isCompleted = currentStep > step.id
        
        return (
          <div key={step.id} className="flex items-center">
            <div className={`flex items-center space-x-2 ${isActive ? 'text-orange-600' : isCompleted ? 'text-green-600' : 'text-gray-400'}`}>
              <div className={`w-10 h-10 rounded-full flex items-center justify-center border-2 ${
                isActive ? 'border-orange-600 bg-orange-50' : 
                isCompleted ? 'border-green-600 bg-green-50' : 
                'border-gray-300 bg-gray-50'
              }`}>
                {isCompleted ? (
                  <CheckCircle className="w-5 h-5" />
                ) : (
                  <Icon className="w-5 h-5" />
                )}
              </div>
              <span className={`text-sm font-medium ${isActive ? 'text-orange-600' : isCompleted ? 'text-green-600' : 'text-gray-500'}`}>
                {step.title}
              </span>
            </div>
            {index < steps.length - 1 && (
              <div className={`w-8 h-0.5 mx-2 ${isCompleted ? 'bg-green-600' : 'bg-gray-300'}`} />
            )}
          </div>
        )
      })}
    </div>
  )

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation */}
      <nav className="bg-gray-900 text-white p-4">
        <div className="container mx-auto flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <Code className="w-6 h-6 text-orange-500" />
            <span className="text-xl font-bold">
              Git<span className="text-orange-500">Snap</span>
            </span>
          </div>
          <Dialog open={showAbout} onOpenChange={setShowAbout}>
            <DialogTrigger asChild>
              <Button variant="ghost" size="sm">
                <Info className="w-4 h-4 mr-2" />
                About
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle className="flex items-center space-x-2">
                  <Info className="w-5 h-5" />
                  <span>About GitSnap</span>
                </DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div>
                  <h4 className="font-semibold mb-2">What is GitSnap?</h4>
                  <p className="text-sm text-gray-600">
                    GitSnap is a powerful tool that transforms complex codebases into accessible, comprehensive tutorials. 
                    It analyzes your repository structure, identifies key abstractions, and generates detailed documentation with interactive diagrams.
                  </p>
                </div>
                <div>
                  <h4 className="font-semibold mb-2">Features:</h4>
                  <ul className="text-sm text-gray-600 space-y-1">
                    <li>• Automatic codebase analysis and documentation generation</li>
                    <li>• Interactive Mermaid diagrams showing code relationships</li>
                    <li>• Support for multiple programming languages</li>
                    <li>• Customizable file filtering and analysis options</li>
                    <li>• Private repository support with GitHub tokens</li>
                  </ul>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </nav>

      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <StepIndicator />

        {/* Step 1: Repository Input */}
        {currentStep === 1 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Github className="w-5 h-5" />
                <span>Repository Information</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 space-y-4">
                  <div>
                    <Label htmlFor="repoUrl">GitHub Repository URL</Label>
                    <Input
                      id="repoUrl"
                      type="url"
                      placeholder="https://github.com/owner/repository"
                      value={repoUrl}
                      onChange={(e) => setRepoUrl(e.target.value)}
                      className={errors.repoUrl ? 'border-red-500' : ''}
                    />
                    {errors.repoUrl && (
                      <p className="text-red-500 text-sm mt-1">{errors.repoUrl}</p>
                    )}
                  </div>
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="isPrivate"
                      checked={isPrivateRepo}
                      onCheckedChange={setIsPrivateRepo}
                    />
                    <Label htmlFor="isPrivate">This is a private repository</Label>
                  </div>
                </div>
                <div>
                  <Card className="bg-blue-50 border-blue-200">
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm">Supported Repositories</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      <div className="flex items-center space-x-2 text-sm">
                        <CheckCircle className="w-4 h-4 text-green-600" />
                        <span>Public GitHub repos</span>
                      </div>
                      <div className="flex items-center space-x-2 text-sm">
                        <CheckCircle className="w-4 h-4 text-green-600" />
                        <span>Private GitHub repos</span>
                      </div>
                      <div className="flex items-center space-x-2 text-sm">
                        <XCircle className="w-4 h-4 text-gray-400" />
                        <span>GitLab (coming soon)</span>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </div>
              <div className="flex justify-end">
                <Button onClick={validateAndProceed} className="bg-orange-600 hover:bg-orange-700">
                  Next <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Step 2: Configuration */}
        {currentStep === 2 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Settings className="w-5 h-5" />
                <span>Analysis Configuration</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Analysis Mode Selection */}
              <div className="space-y-4">
                <div>
                  <Label className="text-base font-semibold">Analysis Mode</Label>
                  <p className="text-sm text-gray-600 mb-3">Choose between quick analysis or comprehensive analysis</p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <Card 
                      className={`cursor-pointer transition-all ${analysisMode === 'fast' ? 'border-orange-500 bg-orange-50' : 'border-gray-200 hover:border-gray-300'}`}
                      onClick={() => setAnalysisMode('fast')}
                    >
                      <CardContent className="p-4">
                        <div className="flex items-start space-x-3">
                          <div className={`w-4 h-4 rounded-full border-2 mt-1 ${analysisMode === 'fast' ? 'border-orange-500 bg-orange-500' : 'border-gray-300'}`}>
                            {analysisMode === 'fast' && <div className="w-2 h-2 bg-white rounded-full m-0.5"></div>}
                          </div>
                          <div className="flex-1">
                            <h3 className="font-semibold text-sm">⚡ Fast Analysis</h3>
                            <p className="text-xs text-gray-600 mt-1">Quick analysis of top 5 files using Gemini 2.5 Flash-Lite Preview</p>
                            <div className="mt-2 space-y-1">
                              <div className="flex items-center text-xs text-green-600">
                                <CheckCircle className="w-3 h-3 mr-1" />
                                <span>Free to use</span>
                              </div>
                              <div className="flex items-center text-xs text-green-600">
                                <CheckCircle className="w-3 h-3 mr-1" />
                                <span>~30 seconds</span>
                              </div>
                              <div className="flex items-center text-xs text-gray-500">
                                <Info className="w-3 h-3 mr-1" />
                                <span>Limited to 5 files</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                    
                    <Card 
                      className={`cursor-pointer transition-all ${analysisMode === 'detailed' ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'}`}
                      onClick={() => setAnalysisMode('detailed')}
                    >
                      <CardContent className="p-4">
                        <div className="flex items-start space-x-3">
                          <div className={`w-4 h-4 rounded-full border-2 mt-1 ${analysisMode === 'detailed' ? 'border-blue-500 bg-blue-500' : 'border-gray-300'}`}>
                            {analysisMode === 'detailed' && <div className="w-2 h-2 bg-white rounded-full m-0.5"></div>}
                          </div>
                          <div className="flex-1">
                            <h3 className="font-semibold text-sm">🔍 Detailed Analysis</h3>
                            <p className="text-xs text-gray-600 mt-1">Comprehensive analysis using your Gemini API key</p>
                            <div className="mt-2 space-y-1">
                              <div className="flex items-center text-xs text-blue-600">
                                <CheckCircle className="w-3 h-3 mr-1" />
                                <span>Unlimited files</span>
                              </div>
                              <div className="flex items-center text-xs text-blue-600">
                                <CheckCircle className="w-3 h-3 mr-1" />
                                <span>Deep insights</span>
                              </div>
                              <div className="flex items-center text-xs text-gray-500">
                                <Key className="w-3 h-3 mr-1" />
                                <span>Requires your API key</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                </div>
                
                {/* API Key Input for Detailed Mode */}
                {analysisMode === 'detailed' && (
                  <div className="space-y-2">
                    <Label htmlFor="userApiKey">Your Gemini API Key</Label>
                    <Input
                      id="userApiKey"
                      type="password"
                      placeholder="AIzaSy..."
                      value={userApiKey}
                      onChange={(e) => setUserApiKey(e.target.value)}
                      className={errors.apiKey ? 'border-red-500' : ''}
                    />
                    {errors.apiKey && (
                      <p className="text-red-500 text-sm">{errors.apiKey}</p>
                    )}
                    <p className="text-sm text-gray-600">
                      Get your free API key from{' '}
                      <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
                        Google AI Studio
                      </a>
                    </p>
                  </div>
                )}
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="includePatterns">File Patterns to Include</Label>
                    <div className="flex space-x-2">
                      <Input
                        id="includePatterns"
                        placeholder="e.g., *.py, *.js"
                        value={currentPattern}
                        onChange={(e) => setCurrentPattern(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && addPattern(currentPattern, 'include')}
                      />
                      <Button 
                        type="button" 
                        variant="outline" 
                        onClick={() => addPattern(currentPattern, 'include')}
                      >
                        Add
                      </Button>
                    </div>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {includePatterns.map((pattern) => (
                        <Badge key={pattern} variant="secondary" className="flex items-center space-x-1">
                          <span>{pattern}</span>
                          <button
                            onClick={() => removePattern(pattern, 'include')}
                            className="text-red-500 hover:text-red-700"
                          >
                            ×
                          </button>
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <div>
                    <Label htmlFor="excludePatterns">File Patterns to Exclude (Optional)</Label>
                    <div className="flex space-x-2">
                      <Input
                        id="excludePatterns"
                        placeholder="e.g., *.test.js, *.spec.py"
                        value={currentExcludePattern}
                        onChange={(e) => setCurrentExcludePattern(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && addPattern(currentExcludePattern, 'exclude')}
                      />
                      <Button 
                        type="button" 
                        variant="outline" 
                        onClick={() => addPattern(currentExcludePattern, 'exclude')}
                      >
                        Add
                      </Button>
                    </div>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {excludePatterns.map((pattern) => (
                        <Badge key={pattern} variant="secondary" className="flex items-center space-x-1">
                          <span>{pattern}</span>
                          <button
                            onClick={() => removePattern(pattern, 'exclude')}
                            className="text-red-500 hover:text-red-700"
                          >
                            ×
                          </button>
                        </Badge>
                      ))}
                    </div>
                  </div>
                </div>
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="maxFileSize">Maximum File Size (bytes)</Label>
                    <Input
                      id="maxFileSize"
                      type="number"
                      value={maxFileSize}
                      onChange={(e) => setMaxFileSize(parseInt(e.target.value))}
                    />
                  </div>
                  <div>
                    <Label htmlFor="language">Tutorial Language</Label>
                    <Select value={language} onValueChange={setLanguage}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="english">English</SelectItem>
                        <SelectItem value="spanish">Spanish</SelectItem>
                        <SelectItem value="french">French</SelectItem>
                        <SelectItem value="german">German</SelectItem>
                        <SelectItem value="chinese">Chinese</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>
              <div className="flex justify-between">
                <Button variant="outline" onClick={() => goToStep(1)}>
                  <ArrowLeft className="w-4 h-4 mr-2" /> Back
                </Button>
                <Button onClick={proceedToAuth} className="bg-orange-600 hover:bg-orange-700">
                  Next <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Step 3: Authentication */}
        {currentStep === 3 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Key className="w-5 h-5" />
                <span>GitHub Authentication</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 space-y-4">
                  <div>
                    <Label htmlFor="githubToken">GitHub Personal Access Token</Label>
                    <Input
                      id="githubToken"
                      type="password"
                      placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                      value={githubToken}
                      onChange={(e) => setGithubToken(e.target.value)}
                      className={errors.token ? 'border-red-500' : ''}
                    />
                    {errors.token && (
                      <p className="text-red-500 text-sm mt-1">{errors.token}</p>
                    )}
                    <p className="text-sm text-gray-600 mt-1">
                      Required for private repositories. 
                      <a href="https://github.com/settings/tokens" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline ml-1">
                        Generate token
                      </a>
                    </p>
                  </div>
                </div>
                <div>
                  <Card className="bg-yellow-50 border-yellow-200">
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm">Token Permissions</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      <p className="text-sm text-gray-600">Your token needs:</p>
                      <div className="space-y-1">
                        <div className="flex items-center space-x-2 text-sm">
                          <CheckCircle className="w-4 h-4 text-green-600" />
                          <span>repo (for private repos)</span>
                        </div>
                        <div className="flex items-center space-x-2 text-sm">
                          <CheckCircle className="w-4 h-4 text-green-600" />
                          <span>public_repo (for public repos)</span>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </div>
              <div className="flex justify-between">
                <Button variant="outline" onClick={() => goToStep(2)}>
                  <ArrowLeft className="w-4 h-4 mr-2" /> Back
                </Button>
                <Button onClick={validateTokenAndProceed} className="bg-orange-600 hover:bg-orange-700">
                  Next <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Step 4: Processing */}
        {currentStep === 4 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Settings2 className="w-5 h-5" />
                <span>Analyzing Codebase</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="text-center space-y-6">
              <div className="flex justify-center">
                <Loader2 className="w-12 h-12 text-orange-600 animate-spin" />
              </div>
              <div>
                <h3 className="text-lg font-semibold mb-2">{analysisMessage}</h3>
                <Progress value={progress} className="w-full max-w-md mx-auto" />
                <p className="text-sm text-gray-600 mt-2">{progress.toFixed(0)}% complete</p>
              </div>
              <p className="text-sm text-gray-500">
                This may take several minutes for large repositories.
              </p>
            </CardContent>
          </Card>
        )}

        {/* Step 5: Results */}
        {currentStep === 5 && (
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="flex items-center space-x-2">
                <FileText className="w-5 h-5" />
                <span>Analysis Results</span>
              </CardTitle>
              <div className="flex space-x-2">
                {isPrivateRepo && results.includes('🔒') && (
                  <Button variant="outline" size="sm" onClick={decryptAndViewResults}>
                    <Key className="w-4 h-4 mr-2" />
                    View Results
                  </Button>
                )}
                <Button variant="outline" size="sm" onClick={downloadResults} disabled={!jobId}>
                  <Download className="w-4 h-4 mr-2" />
                  Download
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {isPrivateRepo && results.includes('🔒') && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                  <div className="flex items-center space-x-2 text-blue-800">
                    <Key className="w-5 h-5" />
                    <span className="font-medium">Private Repository</span>
                  </div>
                  <p className="text-sm text-blue-700 mt-2">
                    Results are encrypted for security. Click "View Results" to decrypt and display the analysis using your GitHub token.
                  </p>
                </div>
              )}
              <div className="bg-gray-50 rounded-lg p-4 max-h-96 overflow-y-auto">
                <pre className="whitespace-pre-wrap text-sm">{results || 'Loading results...'}</pre>
              </div>
              <div className="mt-4 flex justify-center">
                <Button onClick={resetApp} className="bg-orange-600 hover:bg-orange-700">
                  Analyze Another Repository
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}

export default App

