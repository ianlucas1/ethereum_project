# Third-Party Software Notices and Information

This project incorporates components from other open source software.
This file contains attributions and license information for third-party
software products or components distributed with this project.

The original copyright notices and license texts for these components
are generally available within their respective source code distributions.

---

## Dependencies

This project relies on several third-party libraries. The primary license for this
project is the MIT License (see the `LICENSE` file in the root directory).
The following are notable licenses of direct dependencies included in the runtime
environment of the distributed Docker image:

1.  **certifi**
    *   License: Mozilla Public License Version 2.0 (MPL-2.0)
    *   Copyright: © 2011-2024 Kenneth Reitz, © 2025 Certifi Core Team
    *   Source: [https://github.com/certifi/python-certifi](https://github.com/certifi/python-certifi)
    *   The MPL-2.0 license text can be found at: [https://www.mozilla.org/en-US/MPL/2.0/](https://www.mozilla.org/en-US/MPL/2.0/)
    *   As per MPL-2.0 Section 3.2, if you distribute this software in an executable
        form (such as this Docker image), you must make the Source Code of the MPL-2.0
        Covered Software available. Certifi is typically distributed as source by pip.

2.  **Pillow (Python Imaging Library Fork)**
    *   License: The Python Imaging Library (PIL) Software License (a permissive, BSD-style license)
    *   Copyright: © 1997-2011 Secret Labs AB, © 1995-2011 Fredrik Lundh, © 2010-2024 Pillow Authors
    *   Source: [https://github.com/python-pillow/Pillow](https://github.com/python-pillow/Pillow)
    *   License Text:
        ```
        The Python Imaging Library (PIL) is
        Copyright © 1997-2011 Secret Labs AB
        Copyright © 1995-2011 Fredrik Lundh
        Copyright © 2010-2024 Pillow Authors

        Like PIL, Pillow is licensed under the open source HPND License (historically
        known as the Python Imaging Library (PIL) Software License).

        Permission to use, copy, modify, and distribute this software and its
        documentation for any purpose and without fee is hereby granted, provided
        that the above copyright notice appear in all copies and that both that
        copyright notice and this permission notice appear in supporting
        documentation, and that the name of Secret Labs AB or the Zen of Python
        not be used in advertising or publicity pertaining to distribution of the
        software without specific, written prior permission.

        SECRET LABS AB AND THE ZEN OF PYTHON DISCLAIMS ALL WARRANTIES WITH REGARD
        TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND
        FITNESS. IN NO EVENT SHALL SECRET LABS AB OR THE ZEN OF PYTHON BE LIABLE
        FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
        WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
        ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
        OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
        ```

---

Many other dependencies are used, as detailed in `requirements-runtime-lock.txt`.
These dependencies are typically licensed under permissive open source licenses
such as MIT, BSD, Apache 2.0, etc. For full details, please refer to the
license files accompanying each individual package, typically found within their
source distributions or Python package metadata.

Examples of other commonly used licenses in the Python ecosystem that may be
present in the transitive dependencies include:
*   MIT License
*   BSD 2-Clause "Simplified" License
*   BSD 3-Clause "New" or "Revised" License
*   Apache License 2.0
*   Python Software Foundation License

Users are encouraged to review the licenses of all included packages if they
have specific G_licensing_S_G compliance requirements.