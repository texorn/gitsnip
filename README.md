# GitSnip

**Turning complex codebases into accessible stories**

[![Watch the GitSnip Demo Video](https://img.youtube.com/vi/p7L3rP_ZJHg/0.jpg)](https://youtu.be/p7L3rP_ZJHg)

![License](https://img.shields.io/badge/license-MIT-blue.svg) 
Automatically generate comprehensive, step-by-step tutorials from any codebase using AI.

## 🤔 About

Understanding large, complex real-world projects is often a developer's nightmare. With minimal documentation and intricate codebases, onboarding to new projects can take weeks of frustrating effort. After repeatedly facing this challenge throughout my career, I realized this widespread problem needed a solution.

That's why I created **GitSnip** - a tool that transforms impenetrable codebases into comprehensible narratives. GitSnip intelligently crawls through entire repositories and generates beautifully structured, story-based explanations of how the code works, complete with detailed explanations, relevant code blocks, and intuitive flow diagrams. What once took days or weeks to grasp can now be understood in hours, making the process of learning a new codebase as enjoyable as reading a well-crafted "lore" rather than a technical chore.

While initially inspired by a basic codebase knowledge generator example from PocketFlow (a 100-line minimalist LLM framework designed for building AI agent workflows), GitSnip represents a complete reimagining of the concept. I've developed advanced capabilities to handle genuinely complex, large-scale projects through sophisticated embedding-based clustering, intelligent content chunking, and cross-reference handling. These enhancements transform the concept from an interesting demo into a powerful tool capable of tackling real-world enterprise codebases that previously required extensive time and expertise to understand.

## 🚀 Features

-   📚 **Automated Tutorial Creation**: Generates multi-chapter Markdown tutorials from source code.
-   🧠 **AI-Powered Analysis**: Leverages LLMs (Gemini) to identify core abstractions and relationships within the code.
-   🔗 **Code Connectivity**: Understands how different parts of the codebase interact.
-   📈 **Visual Structure**: Creates Mermaid diagrams to visualize project architecture and component relationships.
-   ✨ **Diagram Validation & Fixing**: Automatically validates and attempts to fix generated Mermaid diagrams using `mmdc`.
-   📂 **Flexible Input**: Works with both local directories and public GitHub repositories.
-  **Large Codebase Handling**: Uses embedding and clustering techniques for codebases exceeding LLM context windows.
-   🌐 **Language Support**: Generate tutorials in different languages (via `--language` flag, applies to generated text).
-   ⚙️ **Configurable**: Filter files using include/exclude patterns and set maximum file size limits.

## ⚙️ Tech Stack

-   🐍 **Backend**: Python 3
-   🌊 **Workflow**: PocketFlow
-   🤖 **AI**: Google Gemini API (via `google-genai`)
-   🐙 **Git Interaction**: PyGithub (for fetching public repo info)
-   📊 **Diagrams**: Mermaid.js (Validation/Fixing via `@mermaid-js/mermaid-cli`)
-   📄 **Configuration**: YAML, python-dotenv

## ✨ How it Works

The tool follows a multi-step process orchestrated by PocketFlow:

1.  **Fetch**: Reads files from a local directory or fetches file details from a public GitHub repository URL.
2.  **Identify Abstractions**: Uses an LLM (Gemini) to analyze the code and identify the core components or concepts. Handles large codebases using embedding clustering.
3.  **Analyze Relationships**: Determines how the identified abstractions interact with each other, again using an LLM. Generates a project summary.
4.  **Order Chapters**: Logically sequences the abstractions for a smooth learning progression.
5.  **Write Chapters**: Generates detailed Markdown content for each abstraction (chapter), including descriptions, code snippets, and Mermaid diagrams illustrating local relationships.
6.  **Combine Tutorial**: Assembles the individual chapters into a final tutorial structure with a `README.md` containing a table of contents and overall project diagram.
7.  **Validate Diagrams**: Runs the `validate_mermaid.py` script to check and attempt to fix syntax errors in all generated Mermaid diagrams within the tutorial files.

## 🛠️ Setup / Local Usage

Follow these steps to set up and run the generator locally.

1.  **Clone the repository**
    ```bash
    git clone <your-repository-url> # Replace with your repo URL
    cd gitsnip # Or your repo directory name
    ```

2.  **Install Python Dependencies**
    It's recommended to use a virtual environment. Choose **one** of the following methods:

    **Method: Using `conda`**
    *(Requires Anaconda or Miniconda installation)*
    ```bash
    # Create the conda environment (replace 'gitsnip' with your preferred name and '3.12' with your Python version)
    conda create --name gitsnip python=3.12
    
    # Activate the environment
    conda activate gitsnip
    
    # Install dependencies using pip within the conda environment
    pip install -r requirements.txt
    ```

3.  **Install Mermaid CLI**
    This is required for the diagram validation/fixing step.
    ```bash
    npm install -g @mermaid-js/mermaid-cli
    ```
    *Note: Requires Node.js and npm to be installed.*

4.  **Add your Gemini API Key**
    Open the file `utils/call_llm.py` and replace the placeholder `"YOUR_API_KEY_HERE"` with your actual Google Gemini API Key.
    ```python
    # Inside utils/call_llm.py
    client = genai.Client(
       Replace default key
        api_key=os.getenv("GEMINI_API_KEY", "YOUR_API_KEY_HERE"), # Or get from environment variable
    )
    ```
    Alternatively, you can set the `GEMINI_API_KEY` environment variable before running the script.
    *   Get your Gemini API Key from [Google AI Studio](https://aistudio.google.com/app/apikey).
    *   Optionally, set the `GITHUB_TOKEN` environment variable for higher rate limits on public repos. This tool currently processes private repositories only via the local directory method.

5.  **Run the Generator**

    > **Note:** The tutorial generation process is comprehensive and involves multiple LLM calls. For large codebases (e.g., >100 files or several MBs of code), generation can take a significant amount of time, potentially **2-3 hours or more**, depending on the codebase size, LLM API speeds, and rate limits. Please be patient!

    *   **For a Local Directory:**
        ```bash
        python main.py --dir /path/to/your/codebase -i "*.py" -o ./output-directory
        ```

    *   **For a Public GitHub Repository:**
        ```bash
        python main.py --repo https://github.com/owner/repo -i "*.ts" -o ./output-directory
        ```

    *   **For a Private GitHub Repository:**
        Processing private GitHub repositories directly via URL is not currently supported by this workflow. Please **clone the private repository to your local machine first** and then use the `--dir` option pointing to the cloned directory path
     *  You can include any extensions after the "-i" argument

6.  **View the Output**
    Navigate to the specified output directory (e.g., `./output-directory/Project_Name`). Open the `README.md` file to start browsing the tutorial. View it in a powerful markdown viewer which can support mermaid diagram rendering. Recommended to use the VSCode extension "Markdown Preview Enhanced" to view the output.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. If you find issues or have suggestions, please open an issue on the repository.

## Acknowledgements

-   Built using the excellent [PocketFlow](https://github.com/The-Pocket/pocketflow) library.
-   Powered by Google's [Gemini](https://deepmind.google.com/technologies/gemini/) models.
-   Diagrams created with [Mermaid.js](https://mermaid.js.org/).

## 🤔 Future Steps

-   Want to wrap this with FAST API and expose it as frontend, so that people can try it out easily without having to run it locally
