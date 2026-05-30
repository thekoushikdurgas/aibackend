"""Prompt templates for Dev AI toolbox (ported from dev-ai reference)."""

from __future__ import annotations


def minify_prompt(code: str, language: str) -> str:
    return f"""
    You are an expert code minifier.
    Minify the following {language} code.
    Remove all unnecessary characters, whitespace, and comments without altering its functionality.
    IMPORTANT: Respond with ONLY the minified code itself. Do not include any explanatory text, markdown formatting (like ```js), or any other characters before or after the code.

    Code to minify:
    ---
    {code}
    ---
    """.strip()


def cheatsheet_prompt(topic: str) -> str:
    return f"""
    You are an expert developer assistant. Create a concise and helpful cheatsheet for the following topic: "{topic}".
    Use markdown formatting, including code blocks for examples.
    Focus on the most important concepts, syntax, and common use cases.
    For "how to start" queries, provide a clear, step-by-step guide.
    IMPORTANT: Respond with ONLY the cheatsheet content in markdown format. Do not include any introductory or concluding remarks like "Here is the cheatsheet...".
    """.strip()


def regex_generate_contents(description: str) -> str:
    return (
        "Based on the following description, generate a JavaScript-compatible "
        f"regular expression and a clear, step-by-step explanation of how it works. "
        f'Description: "{description}"'
    )


REGEX_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "regex": {
            "type": "STRING",
            "description": "The generated regular expression pattern, without slashes.",
        },
        "explanation": {
            "type": "STRING",
            "description": "A detailed but easy-to-understand explanation of the regex pattern.",
        },
    },
    "required": ["regex", "explanation"],
}


def regex_explain_prompt(regex: str) -> str:
    return f"""
    You are a regular expression expert. Explain the following regex pattern in a clear, step-by-step manner.
    Break down each part of the pattern and describe what it does.
    Use markdown for formatting.

    Regex to explain: `{regex}`
    """.strip()


def json_to_type_prompt(json_string: str, type_system: str, root_type_name: str) -> str:
    root = root_type_name or "RootType"
    return f"""
    You are a code generation expert. Analyze the provided JSON object and generate a corresponding type definition.

    - Target System: {type_system}
    - Root Type Name: {root}
    - JSON Input:
    ```json
    {json_string}
    ```

    Rules:
    - Infer types as accurately as possible (string, number, boolean, array, object).
    - Handle nested objects by creating separate type/schema definitions.
    - If generating a Zod schema, ensure you include `import {{ z }} from 'zod';` at the top.
    - Respond with ONLY the generated code. Do not include any explanations or markdown formatting like ```typescript.
    """.strip()


def refactor_prompt(code: str, language: str, instructions: str) -> str:
    instr = instructions or "Improve readability, maintainability, and performance."
    return f"""
    You are an expert software engineer specializing in code quality and refactoring.
    Refactor the following {language} code based on the provided instructions.

    Instructions: "{instr}"

    Code to refactor:
    ```{language.lower()}
    {code}
    ```

    Rules:
    - The refactored code must maintain the original functionality.
    - Apply modern best practices for the specified language.
    - Add comments only where necessary to clarify complex logic.
    - Respond with ONLY the refactored code. Do not include any explanations or markdown formatting.
    """.strip()


def html_to_code_prompt(html: str) -> str:
    return f"""
      You are an expert web developer. Based on the following HTML content, generate a single, self-contained HTML file.
      This file should include the necessary HTML structure, embedded CSS within a <style> tag, and JavaScript within a <script> tag
      to visually and functionally replicate the original page as closely as possible.

      Focus on recreating the layout, styling, and basic interactivity. You may omit external scripts or complex application logic that cannot be replicated.

      IMPORTANT: Respond with ONLY the generated code inside a single HTML block. Do not include any introductory text or markdown formatting like ```html.

      Original HTML:
      ---
      {html}
      ---
    """.strip()


def enhance_prompt_text(prompt: str) -> str:
    return f"""
        You are an expert prompt engineer. Your task is to enhance the following user prompt to make it more specific, clear, and effective for a large language model.
        The enhanced prompt should:
        - Provide clear context.
        - Define the persona the AI should adopt.
        - Include specific constraints and requirements.
        - Specify the desired output format (e.g., markdown, JSON, bullet points).
        - Use clear and unambiguous language.

        Original User Prompt:
        ---
        {prompt}
        ---

        IMPORTANT: Respond with ONLY the enhanced prompt itself. Do not include any explanatory text, markdown formatting, or any other characters before or after the enhanced prompt.
    """.strip()


def memory_title_prompt(content: str, memory_type: str) -> str:
    return f"""
        You are a helpful assistant that generates a short, concise, and descriptive title (maximum 6 words) for the following saved memory.
        The memory type is: {memory_type}.

        Memory Content:
        ---
        {content}
        ---

        IMPORTANT: Respond with ONLY the title itself. Do not include any quotes, markdown formatting, or any extra text.
    """.strip()


def ceto_prompts_text(topic: str) -> str:
    return f"""
        You are an expert in prompt engineering specializing in the CETO (Context, Example, Task, Output) framework.
        For the given topic, generate two distinct, high-quality, CETO-structured prompts.

        Topic: "{topic}"

        For each generated prompt, follow this structure precisely:
        **Prompt [Number]: [Brief Title for the Prompt]**
        - **Context:** [Provide the background and scenario for the AI.]
        - **Example:** [Provide a clear, concise example of the desired input/output or style.]
        - **Task:** [State the specific action the AI needs to perform.]
        - **Output:** [Describe the desired format, structure, and constraints for the AI's response.]

        Ensure the generated prompts are practical and well-defined.
        Respond ONLY with the markdown-formatted prompts. Do not include any introductory or concluding remarks.
    """.strip()
