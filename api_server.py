#!/usr/bin/env python3
"""
GitSnip Flask API Server
Provides REST API endpoints for the GitSnip codebase analysis tool
"""

from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import os
import subprocess
import uuid
import threading
import time
import shutil
import tempfile
import json
import glob
import base64
import hashlib
from datetime import datetime
from pathlib import Path
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from job_manager import job_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
OUTPUT_DIR = os.path.join(os.getcwd(), "output")
TEMP_DIR = os.path.join(os.getcwd(), "temp")
DATA_DIR = os.path.join(os.getcwd(), "data")

# Ensure directories exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

def generate_encryption_key(github_token, salt=None):
    """Generate encryption key from GitHub token"""
    if salt is None:
        salt = b'gitsnip_salt_2024'  # Use a consistent salt for the same token
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(github_token.encode()))
    return key

def encrypt_data(data, github_token):
    """Encrypt data using GitHub token as key"""
    try:
        key = generate_encryption_key(github_token)
        fernet = Fernet(key)
        
        if isinstance(data, str):
            data = data.encode()
        elif isinstance(data, dict):
            data = json.dumps(data).encode()
        
        encrypted_data = fernet.encrypt(data)
        return base64.urlsafe_b64encode(encrypted_data).decode()
    except Exception as e:
        logger.error(f"Encryption error: {str(e)}")
        raise

def decrypt_data(encrypted_data, github_token):
    """Decrypt data using GitHub token as key"""
    try:
        key = generate_encryption_key(github_token)
        fernet = Fernet(key)
        
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
        decrypted_data = fernet.decrypt(encrypted_bytes)
        
        return decrypted_data.decode()
    except Exception as e:
        logger.error(f"Decryption error: {str(e)}")
        raise

def encrypt_file(file_path, github_token):
    """Encrypt a file and return encrypted content"""
    try:
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        key = generate_encryption_key(github_token)
        fernet = Fernet(key)
        encrypted_content = fernet.encrypt(file_content)
        
        return base64.urlsafe_b64encode(encrypted_content).decode()
    except Exception as e:
        logger.error(f"File encryption error: {str(e)}")
        raise

def create_encrypted_archive(directory_path, github_token):
    """Create an encrypted ZIP archive of a directory"""
    try:
        # Create temporary ZIP file
        temp_zip = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
        temp_zip.close()
        
        # Create ZIP archive
        shutil.make_archive(temp_zip.name.replace('.zip', ''), 'zip', directory_path)
        
        # Read and encrypt the ZIP file
        with open(temp_zip.name, 'rb') as f:
            zip_content = f.read()
        
        key = generate_encryption_key(github_token)
        fernet = Fernet(key)
        encrypted_zip = fernet.encrypt(zip_content)
        
        # Clean up temp file
        os.unlink(temp_zip.name)
        
        return base64.urlsafe_b64encode(encrypted_zip).decode()
    except Exception as e:
        logger.error(f"Archive encryption error: {str(e)}")
        raise

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'gitsnip-backend',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })

@app.route('/api/gitsnip/analyze', methods=['POST'])
def start_analysis():
    """Start GitSnip analysis for a repository"""
    try:
        data = request.json
        repo_url = data.get('repository_url')
        config = data.get('config', {})
        analysis_mode = data.get('analysis_mode', 'fast')  # Default to fast mode
        user_api_key = data.get('user_api_key')  # For detailed analysis
        
        if not repo_url:
            return jsonify({'error': 'Repository URL is required'}), 400
        
        # Validate analysis mode
        if analysis_mode not in ['fast', 'detailed']:
            return jsonify({'error': 'Analysis mode must be "fast" or "detailed"'}), 400
        
        # For detailed analysis, require user API key
        if analysis_mode == 'detailed' and not user_api_key:
            return jsonify({'error': 'User API key is required for detailed analysis'}), 400
        
        # Validate repository URL
        if not (repo_url.startswith('https://github.com/') or repo_url.startswith('http://github.com/')):
            return jsonify({'error': 'Only GitHub repositories are supported'}), 400
        
        # Create job using job manager
        job_config = {
            'include_patterns': config.get('include_patterns', ['*.py']),
            'exclude_patterns': config.get('exclude_patterns', []),
            'max_file_size': config.get('max_file_size', 100000),
            'language': config.get('language', 'english'),
            'api_key': user_api_key
        }
        
        job_id = job_manager.create_job(repo_url, analysis_mode, job_config)
        
        # Start analysis in background thread
        thread = threading.Thread(target=run_gitsnip_analysis, args=(job_id, repo_url, job_config, analysis_mode, user_api_key))
        thread.daemon = True
        thread.start()
        
        logger.info(f"Started {analysis_mode} analysis job {job_id} for repository {repo_url}")
        
        return jsonify({
            'job_id': job_id,
            'status': 'pending',
            'message': f'{analysis_mode.title()} analysis started',
            'analysis_mode': analysis_mode,
            'redirect_url': f'/job/{job_id}'
        }), 202
        
    except Exception as e:
        logger.error(f"Error starting analysis: {str(e)}")
        return jsonify({'error': f'Failed to start analysis: {str(e)}'}), 500

@app.route('/api/gitsnip/status/<job_id>', methods=['GET'])
def get_status(job_id):
    """Get job status and progress"""
    job_data = job_manager.get_job(job_id)
    
    if not job_data:
        return jsonify({'error': 'Job not found'}), 404
    
    return jsonify({
        'job_id': job_id,
        'status': job_data['status'],
        'progress': job_data['progress'],
        'message': job_data['message'],
        'created_at': job_data['created_at'],
        'updated_at': job_data['updated_at'],
        'analysis_mode': job_data['analysis_mode'],
        'repository_url': job_data['repository_url']
    })

@app.route('/api/gitsnip/results/<job_id>', methods=['GET'])
def get_results(job_id):
    """Get analysis results"""
    job_data = job_manager.get_job(job_id)
    
    if not job_data:
        return jsonify({'error': 'Job not found'}), 404
    
    if job_data['status'] != 'completed':
        return jsonify({
            'error': 'Analysis not completed yet',
            'status': job_data['status'],
            'progress': job_data['progress'],
            'message': job_data['message']
        }), 400
    
    return jsonify({
        'job_id': job_id,
        'status': job_data['status'],
        'repository_url': job_data['repository_url'],
        'analysis_mode': job_data['analysis_mode'],
        'results': job_data['result'],
        'completed_at': job_data['updated_at']
    })

@app.route('/api/jobs', methods=['GET'])
def list_jobs():
    """Get list of recent jobs"""
    limit = request.args.get('limit', 50, type=int)
    jobs = job_manager.get_job_list(limit)
    
    return jsonify({
        'jobs': jobs,
        'total': len(jobs)
    })

@app.route('/api/gitsnip/results/<job_id>', methods=['GET'])
def get_results(job_id):
    """Get analysis results"""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = jobs[job_id]
    if job['status'] != 'completed':
        return jsonify({'error': 'Analysis not completed yet'}), 400
    
    # Check if this is a private repository
    is_private = job.get('config', {}).get('is_private', False)
    
    if is_private:
        # For private repos, return encrypted results
        return jsonify({
            'job_id': job_id,
            'status': job['status'],
            'repository_url': job['repository_url'],
            'is_private': True,
            'encrypted_results': job.get('encrypted_results'),
            'completed_at': job.get('completed_at'),
            'download_url': f'/api/gitsnip/download/{job_id}'
        })
    else:
        # For public repos, return results normally
        return jsonify({
            'job_id': job_id,
            'status': job['status'],
            'repository_url': job['repository_url'],
            'is_private': False,
            'results': job['results'],
            'completed_at': job.get('completed_at'),
            'download_url': f'/api/gitsnip/download/{job_id}'
        })

@app.route('/api/gitsnip/decrypt/<job_id>', methods=['POST'])
def decrypt_results(job_id):
    """Decrypt results for private repositories"""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = jobs[job_id]
    if job['status'] != 'completed':
        return jsonify({'error': 'Analysis not completed yet'}), 400
    
    if not job.get('config', {}).get('is_private', False):
        return jsonify({'error': 'This is not a private repository'}), 400
    
    try:
        data = request.json
        github_token = data.get('github_token')
        
        if not github_token:
            return jsonify({'error': 'GitHub token is required for decryption'}), 400
        
        # Verify this is the same token used for encryption
        original_token = job.get('config', {}).get('github_token')
        if not original_token or github_token != original_token:
            return jsonify({'error': 'Invalid GitHub token'}), 403
        
        # Decrypt the results
        encrypted_results = job.get('encrypted_results')
        if not encrypted_results:
            return jsonify({'error': 'No encrypted results found'}), 404
        
        decrypted_results = decrypt_data(encrypted_results, github_token)
        results = json.loads(decrypted_results)
        
        return jsonify({
            'job_id': job_id,
            'status': job['status'],
            'repository_url': job['repository_url'],
            'results': results,
            'completed_at': job.get('completed_at')
        })
        
    except Exception as e:
        logger.error(f"Decryption error for job {job_id}: {str(e)}")
        return jsonify({'error': 'Failed to decrypt results. Please check your GitHub token.'}), 400

@app.route('/api/gitsnip/download/<job_id>', methods=['GET', 'POST'])
def download_results(job_id):
    """Download analysis results as ZIP file"""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = jobs[job_id]
    if job['status'] != 'completed':
        return jsonify({'error': 'Analysis not completed yet'}), 400
    
    is_private = job.get('config', {}).get('is_private', False)
    
    if is_private:
        # For private repos, require GitHub token for decryption
        if request.method == 'GET':
            return jsonify({
                'error': 'GitHub token required for private repository download',
                'requires_token': True
            }), 400
        
        try:
            data = request.json
            github_token = data.get('github_token')
            
            if not github_token:
                return jsonify({'error': 'GitHub token is required'}), 400
            
            # Verify token
            original_token = job.get('config', {}).get('github_token')
            if not original_token or github_token != original_token:
                return jsonify({'error': 'Invalid GitHub token'}), 403
            
            # Get encrypted archive
            encrypted_archive = job.get('encrypted_archive')
            if not encrypted_archive:
                return jsonify({'error': 'No encrypted archive found'}), 404
            
            # Decrypt and create download
            try:
                key = generate_encryption_key(github_token)
                fernet = Fernet(key)
                
                encrypted_bytes = base64.urlsafe_b64decode(encrypted_archive.encode())
                decrypted_zip = fernet.decrypt(encrypted_bytes)
                
                # Create temporary file for download
                temp_file = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
                temp_file.write(decrypted_zip)
                temp_file.close()
                
                return send_file(
                    temp_file.name,
                    as_attachment=True,
                    download_name=f"gitsnip_analysis_{job_id}.zip",
                    mimetype='application/zip'
                )
                
            except Exception as e:
                logger.error(f"Decryption error: {str(e)}")
                return jsonify({'error': 'Failed to decrypt archive'}), 400
                
        except Exception as e:
            logger.error(f"Download error for private repo: {str(e)}")
            return jsonify({'error': 'Download failed'}), 500
    
    else:
        # For public repos, normal download
        output_dir = job.get('output_dir')
        if not output_dir or not os.path.exists(output_dir):
            return jsonify({'error': 'Results not found'}), 404
        
        try:
            # Create ZIP file
            zip_path = f"{TEMP_DIR}/{job_id}_results.zip"
            shutil.make_archive(zip_path.replace('.zip', ''), 'zip', output_dir)
            
            return send_file(
                zip_path,
                as_attachment=True,
                download_name=f"gitsnip_analysis_{job_id}.zip",
                mimetype='application/zip'
            )
        except Exception as e:
            logger.error(f"Error creating download: {str(e)}")
            return jsonify({'error': 'Failed to create download'}), 500

@app.route('/api/gitsnip/jobs', methods=['GET'])
def list_jobs():
    """List all analysis jobs"""
    job_list = []
    for job_id, job in jobs.items():
        job_list.append({
            'job_id': job_id,
            'status': job['status'],
            'repository_url': job['repository_url'],
            'created_at': job['created_at'],
            'progress': job['progress']
        })
    
    return jsonify({'jobs': job_list})

def run_gitsnip_analysis(job_id, repo_url, config, analysis_mode='fast', user_api_key=None):
    """Run the actual GitSnip analysis"""
    try:
        # Update status
        job_manager.update_job_status(job_id, 'running', 5, f'Preparing {analysis_mode} analysis environment...')
        
        # Create unique output directory for this job
        job_output_dir = os.path.join(OUTPUT_DIR, job_id)
        os.makedirs(job_output_dir, exist_ok=True)
        
        # Build GitSnip command
        cmd = [
            'python3', 'main.py',
            '--repo', repo_url,
            '--output', job_output_dir,
            '--analysis-mode', analysis_mode
        ]
        
        # Add user API key for detailed analysis
        if analysis_mode == 'detailed' and user_api_key:
            os.environ['USER_GEMINI_API_KEY'] = user_api_key
        
        # Add configuration options
        if config.get('include_patterns'):
            for pattern in config['include_patterns']:
                cmd.extend(['--include', pattern])
        
        if config.get('exclude_patterns'):
            for pattern in config['exclude_patterns']:
                cmd.extend(['--exclude', pattern])
        
        # Set file size limits based on analysis mode
        if analysis_mode == 'fast':
            # Fast mode: smaller file size limit
            max_file_size = config.get('max_file_size', 10000)  # 10KB default for fast
        else:
            # Detailed mode: larger file size limit
            max_file_size = config.get('max_file_size', 50000)  # 50KB default for detailed
        
        cmd.extend(['--max-size', str(max_file_size)])
        
        if config.get('language'):
            cmd.extend(['--language', config['language']])
        
        logger.info(f"Running GitSnip command ({analysis_mode} mode): {' '.join(cmd)}")
        
        # Update status
        job_manager.update_job_status(job_id, 'running', 10, f'Starting {analysis_mode} GitSnip analysis...')
        
        # Run GitSnip with progress monitoring
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd='/app'
        )
        
        # Monitor progress (different steps for different modes)
        if analysis_mode == 'fast':
            progress_steps = [
                (20, 'Cloning repository...'),
                (40, 'Analyzing top 5 files...'),
                (60, 'Generating quick summary...'),
                (80, 'Creating fast documentation...'),
                (95, 'Finalizing quick analysis...')
            ]
        else:
            progress_steps = [
                (20, 'Cloning repository...'),
                (35, 'Analyzing code structure...'),
                (50, 'Identifying abstractions...'),
                (65, 'Analyzing relationships...'),
                (80, 'Generating comprehensive documentation...'),
                (95, 'Creating detailed diagrams...')
            ]
        
        for progress, message in progress_steps:
            if process.poll() is None:  # Process still running
                job_manager.update_job_status(job_id, 'running', progress, message)
                time.sleep(2)  # Simulate time for each step
        
        # Wait for process to complete
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            # Analysis completed successfully
            job_manager.update_job_status(job_id, 'running', 98, 'Finalizing results...')
            
            # Parse results
            results = parse_gitsnip_results(job_output_dir, repo_url, analysis_mode)
            
            # Complete the job
            job_manager.complete_job(job_id, results)
            logger.info(f"{analysis_mode.title()} analysis job {job_id} completed successfully")
            
        else:
            # Analysis failed
            error_message = stderr or stdout or 'Unknown error occurred'
            job_manager.fail_job(job_id, f'{analysis_mode.title()} analysis failed: {error_message}')
            logger.error(f"{analysis_mode.title()} analysis job {job_id} failed: {error_message}")
            
    except Exception as e:
        error_message = f'{analysis_mode.title()} analysis failed: {str(e)}'
        job_manager.fail_job(job_id, error_message)
        logger.error(f"{analysis_mode.title()} analysis job {job_id} failed with exception: {str(e)}")

def parse_gitsnip_results(output_dir, repo_url, analysis_mode='fast'):
    """Parse GitSnip analysis results"""
    try:
        results = {
            'repository_url': repo_url,
            'analysis_mode': analysis_mode,
            'analysis_summary': {},
            'files': [],
            'documentation': []
        }
        
        # Look for README.md in output directory
        readme_path = os.path.join(output_dir, 'README.md')
        if os.path.exists(readme_path):
            with open(readme_path, 'r', encoding='utf-8') as f:
                readme_content = f.read()
                results['analysis_summary']['readme'] = readme_content[:1000] + '...' if len(readme_content) > 1000 else readme_content
        
        # Count generated files
        markdown_files = glob.glob(os.path.join(output_dir, '**/*.md'), recursive=True)
        results['files'] = [os.path.relpath(f, output_dir) for f in markdown_files]
        
        # Extract project info from directory structure
        project_dirs = [d for d in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, d))]
        if project_dirs:
            project_name = project_dirs[0]
            results['analysis_summary']['project_name'] = project_name
            
            # Count files in project directory
            project_path = os.path.join(output_dir, project_name)
            if os.path.exists(project_path):
                all_files = glob.glob(os.path.join(project_path, '**/*'), recursive=True)
                results['analysis_summary']['total_files'] = len([f for f in all_files if os.path.isfile(f)])
        
        # Basic statistics with mode-specific info
        results['analysis_summary'].update({
            'generated_files': len(markdown_files),
            'analysis_date': datetime.utcnow().isoformat(),
            'analysis_mode': analysis_mode,
            'mode_description': 'Quick analysis with top 5 files' if analysis_mode == 'fast' else 'Comprehensive analysis with detailed insights',
            'status': 'completed'
        })
        
        return results
        
    except Exception as e:
        logger.error(f"Error parsing results: {str(e)}")
        return {
            'repository_url': repo_url,
            'analysis_mode': analysis_mode,
            'error': f'Failed to parse results: {str(e)}',
            'analysis_date': datetime.utcnow().isoformat()
        }

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 4000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    logger.info(f"Starting GitSnip API server on port {port}")
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info(f"Temp directory: {TEMP_DIR}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)