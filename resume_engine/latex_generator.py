class LatexResumeGenerator:
    def __init__(self, name: str, email: str, phone: str, github: str, linkedin: str):
        self.name = name
        self.email = email
        self.phone = phone
        self.github = github
        self.linkedin = linkedin

    def generate_latex(self, matched_skills: list, job_title: str, company: str) -> str:
        def escape(value) -> str:
            replacements = {
                "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
                "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
                "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
            }
            return "".join(replacements.get(char, char) for char in str(value or ""))

        skills_formatted = ", ".join(escape(skill) for skill in matched_skills) if matched_skills else "Embedded C, RTOS, ARM Cortex, Microcontrollers, SPI, I2C, UART"
        name, email, phone = escape(self.name), escape(self.email), escape(self.phone)
        github, linkedin = escape(self.github), escape(self.linkedin)
        job_title, company = escape(job_title), escape(company)

        latex_code = f"""\\documentclass[letterpaper,11pt]{{article}}
\\usepackage{{latexsym}}
\\usepackage[empty]{{fullpage}}
\\usepackage{{titlesec}}
\\usepackage{{marvosym}}
\\usepackage[usenames,dvipsnames]{{color}}
\\usepackage{{verbatim}}
\\usepackage{{enumitem}}
\\usepackage[hidelinks]{{hyperref}}
\\usepackage{{fancyhdr}}
\\usepackage[english]{{babel}}
\\usepackage{{tabularx}}

\\pagestyle{{fancy}}
\\fancyhf{{}} 
\\fancyfoot{{}}
\\renewcommand{{\\headrulewidth}}{{0pt}}
\\renewcommand{{\\footrulewidth}}{{0pt}}

\\addtolength{{\\oddsidemargin}}{{-0.5in}}
\\addtolength{{\\evensidemargin}}{{-0.5in}}
\\addtolength{{\\textwidth}}{{1in}}
\\addtolength{{\\topmargin}}{{-.5in}}
\\addtolength{{\\textheight}}{{1.0in}}

\\urlstyle{{same}}
\\raggedbottom
\\raggedright
\\setlength{{\\tabcolsep}}{{0pt}}

\\begin{{document}}

\\begin{{center}}
    {{\\Huge \\scshape {name}}} \\\\ \\vspace{{1pt}}
    \\small {phone} $|$ \\href{{mailto:{email}}}{{{email}}} $|$ 
    \\href{{{linkedin}}}{{LinkedIn}} $|$
    \\href{{{github}}}{{GitHub}}
\\end{{center}}

\\section{{Objective}}
Detail-oriented Electronics and Communication Graduate aiming for the \\textbf{{{job_title}}} position at \\textbf{{{company}}}. Proficient in firmware development and low-level system programming.

\\section{{Technical Skills}}
 \\begin{{itemize}}[leftmargin=0.15in, label={{}}]
    \\small{{\\item{{
     \\textbf{{Target Core Skills}} : {{{skills_formatted}}} \\\\
     \\textbf{{Languages}} : C, C++, Python, Assembly \\\\
     \\textbf{{Hardware Platforms}} : ARM Cortex-M, STM32, ESP32, Arduino \\\\
     \\textbf{{Protocols/Tools}} : UART, SPI, I2C, CAN, Git, GDB, Oscilloscope
    }}}}
 \\end{{itemize}}

\\end{{document}}
"""

        return latex_code
