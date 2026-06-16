# COBOL Handbook — Batch and CICS
# The 20 COBOL Coding Rules

Every rule applies to every program written or reviewed. No exceptions.

### Structure

#### Rule 1 — SECTIONs only, no paragraphs
Every unit of code is a SECTION.

*Why.* Paragraphs allow fall-through into the next paragraph; SECTIONs do not. Removes a class of control-flow bugs.

#### Rule 2 — Plain `PERFORM <section-name>` only
No `PERFORM ... THRU`.

*Why.* `THRU` collapses code boundaries and creates dependencies on lexical order. Plain `PERFORM` keeps each section self-contained.

#### Rule 3 — One label per section
The exit label at the bottom. No intermediate labels inside a section body.

*Why.* Intermediate labels invite `GOTO`. Single entry and single exit per section is the precondition for the other rules.

#### Rule 4 — No GOTO
Use `EXIT SECTION` to leave a section early, `EXIT PERFORM` to leave a loop early.

*Why.* Structured early exit is unambiguous. `GOTO` encourages spaghetti and undermines Rule 3.

#### Rule 5 — 4-digit numeric prefix on every section name
Each prefix is unique within the program.

| Range | Purpose |
|---|---|
| `0000` | Main program |
| `01xx`–`89xx` | Functional sections (grouped by hundreds) |
| `9xxx` | Reserved for service / common sections |

Reserved service prefixes — use these exact numbers when the section exists; do not renumber:

| Prefix | Purpose |
|---|---|
| `9000` | Trace / logging (`9000-TRACE-HANDLING`) |
| `9010` | CICS response check (`9010-CHECK-CICS-RESPONSE`) |
| `9020` | Batch file status check (`9020-CHECK-FILE-STATUS`) *or* CICS EZASOKET response check (`9020-CHECK-EZA-RESPONSE`) — pick one per program |
| `9990` | Pseudo-conversational return (`9990-RETURN-CONVERSATIONAL`) |
| `9998` | Abnormal termination (GOBACK — never returns) |
| `9999` | Normal termination (GOBACK) |

Other `9xxx` prefixes are free for additional service sections. Pick a number that doesn't collide.

*Why uniqueness.* `PERFORM` targets sections by name; shared prefixes force readers to disambiguate by suffix only. Uniqueness keeps the prefix a reliable index into the program.

*Why the schema.* It encodes severity and stage. A reader sees `9998-...` and knows control will not return; `9xxx` flags "this is plumbing, not business logic."

### Statements and delimiters

#### Rule 6 — No dot (period) unless required by syntax
A dot is only valid after `SECTION.` headers and after exit labels (`nnnn-EXIT. EXIT.`). Never use a dot to close an `IF`, `PERFORM`, `EVALUATE`, `READ`, or any structured block.

*Why.* A misplaced dot silently terminates the enclosing scope and lets following statements escape it. Eliminating dots eliminates the entire class of bug.

#### Rule 7 — Always use full structured delimiters
`END-IF`, `END-PERFORM`, `END-EVALUATE`, `END-EXEC`, `END-CALL`, etc.

*Why.* Explicit terminators are unambiguous. Implicit termination by the next statement or by period is the source of most COBOL maintenance defects.

### Main program flow

#### Rule 8 — Flat `0000-MAIN-PROGRAM`
A flat sequence of `PERFORM`s, no error checks after each. Any error inside a called section calls `PERFORM 9998-ABNORMAL-TERMINATION` (which never returns), so RC checks after `PERFORM` are dead code. High-level principal control flow (e.g. `IF NO-COMMANDS-FOUND`) is fine in `0000-MAIN`; error checking is not.

*Why.* All errors funnel through `9998`. Repeated `IF`-RC checks after every `PERFORM` are noise and obscure the program shape.

### Logic and data

#### Rule 9 — No magic constants
Use 88-level condition names.

```cobol
03 WS-STATUS        PIC X(01).
  88 STATUS-OK      VALUE 'O'.
  88 STATUS-ERROR   VALUE 'E'.
...
IF STATUS-ERROR ...
```

*Why.* Magic literals scattered through the code drift out of sync. Named conditions are checked once at definition.

#### Rule 10 — Prefer EVALUATE over IF for multi-branch logic
Use `IF` only for a single-condition check. **Every `EVALUATE` must have an explicit `WHEN OTHER`** — even if it is `CONTINUE` or a trace.

*Why.* `EVALUATE TRUE` reads like a decision table; nested IFs do not. A missing `WHEN OTHER` is the COBOL equivalent of a fall-through `switch` — every real-world bug eventually lands in it.

**Long IF/ELSE — annotate or refactor.** If the `ELSE` of an `IF` is more than ~10–15 lines below the `IF` (the reader has to scroll back to remember the condition), do ONE of:

1. **Convert to `EVALUATE TRUE`** with explicit `WHEN` clauses. Best when each branch is a self-contained block.
2. **Add a trailing `*>` comment to the `ELSE`** stating the implicit condition. Acceptable when the IF is genuinely two-branch.

The trailing comment must stay within col 72:

```cobol
           IF EZA-RETCODE < ZERO
               ... 30 lines ...
           ELSE                                    *> RECV succeeded
               ... success path ...
           END-IF
```

#### Rule 11 — Default DISPLAY for working storage; use COMP only when required

- **Default:** unsigned `PIC 9(n)` for flags, counters, accumulators, return codes. For signed cases use `PIC S9(n) SIGN IS LEADING SEPARATE`.
- **Required `COMP` cases:** system interface fields (EZA-\*, EIB fields, RESP / RESP2, DFH\*), pointers / addresses, subscripts inside tight loops, file-record fields where storage size matters at volume.
- **Vendor copybooks are exempt** — never redefine fields the system writes.
- **`COMP` / `COMP-3` fields need a display sidecar before `STRING` or `DISPLAY`:**

```cobol
MOVE EZA-ERRNO TO WS-ERRNO-D    *> WS-ERRNO-D PIC 9(09)
STRING 'ERRNO=' WS-ERRNO-D ...
```

PIC pattern reference for sidecars:

- **Unsigned (always ≥ 0):** `PIC 9(n)` — no S prefix, no editing symbol.
- **Signed (can go negative):** `PIC -9(n)` — editing picture; prints `-` or space.

*Why.* The performance argument for `COMP` does not survive measurement on Rocket Enterprise Server (operations are software-emulated on x86-64). The manipulation cost of `COMP` is paid every time the field is traced, `STRING`'d, or inspected in a debug dump.

### CICS

#### Rule 12 — No `EXEC CICS HANDLE CONDITION`
Every `EXEC CICS` includes `RESP(WS-RESPONSE) RESP2(WS-RESPONSE-2)` and is checked explicitly after.

**Exception — `EXEC CICS ADDRESS EIB`:** must be issued **bare** — no `RESP`/`RESP2`. CICS writes RESP into EIB fields, which are not yet addressable before this call completes. Adding `RESP`/`RESP2` here abends.

```cobol
           EXEC CICS ADDRESS EIB(EIB-BLOCK-ADDR)
           END-EXEC

           SET ADDRESS OF DFHEIBLK TO EIB-BLOCK-ADDR
```

*Why.* `HANDLE CONDITION` is invisible flow control. Inline `RESP` checks put the error path next to the call.

#### Rule 13 — Bracket every `EXEC CICS` with an action label
Check inline. Set `WS-COMMAND` and `WS-OBJECT` before the call so error messages are self-describing. Standard `9010-CHECK-CICS-RESPONSE` section described in §7.1.

*Why.* The action label is the breadcrumb. Without it, an error message says "RESP=44" with no context.

### Batch I/O

#### Rule 14 — Bracket every batch I/O with an action label and a check PERFORM
Set `WS-COMMAND` and `WS-OBJECT` before the I/O statement so error messages name what failed. Standard `9020-CHECK-FILE-STATUS` section described in §6.1.

*Why.* The action label is the breadcrumb. Without `WS-COMMAND` / `WS-OBJECT`, an error message says "STATUS=23" with no context.

### Spacing

#### Rule 15 — One blank line before and after every control-flow statement
Applies to: standalone `PERFORM`, block `PERFORM`/`END-PERFORM`, `CALL`/`END-CALL`, `EXEC`/`END-EXEC`, `EXIT SECTION`, `EXIT PERFORM`. Never two consecutive blank lines.

*Why.* Control-flow statements stand out visually. The `/cobol-format` tool enforces this automatically — follow it by hand when writing new code.

### Calls

#### Rule 16 — Never CALL with a string literal
Always use a `PIC X(08)` variable.

```cobol
03 WS-WHOAMI-PGM    PIC X(08) VALUE 'WHOAMI  '.
...
CALL WS-WHOAMI-PGM USING WS-WHOAMI-BUFFER
```

*Why.* Rule 9 (no magic constants) applied to program names. Renaming a called program touches one declaration, not every call site.

### Copybooks

#### Rule 17 — `COPY` statement column aligned to the natural column of the first item in the copybook

| First item in copybook | Natural column | Example |
|---|---|---|
| Level 01 (Area A) | 8 | `COPY TCPEZAC.` |
| Level 03 (Area B) | 12 | `   COPY MYFIELDS.` |
| Level 05 | 16 | `       COPY SUBGROUP.` |

*Why.* The structural intent is visible without opening the copybook. A reader sees the indentation and knows what level it provides.

### Callable programs

#### Rule 18 — Every callable program defines a `WS-FIRST-CALL` flag and checks it in `0010-INITIALIZE`

```cobol
03 WS-FIRST-CALL    PIC 9(01) VALUE ZERO.
  88 FIRST-CALL     VALUE ZERO.
  88 NOT-FIRST-CALL VALUE 1.
...
IF FIRST-CALL
    SET NOT-FIRST-CALL TO TRUE
    *> one-time init
ELSE
    EXIT SECTION
END-IF
```

*Why.* CICS pseudo-conversational calls, loops invoking the same utility, and retry patterns all hit `0010` repeatedly. One-time init must not run twice.

### Size and complexity

#### Rule 19 — Prefer short sections and shallow nesting
Soft target ~100 statements per section, ~3 levels of `IF` / `EVALUATE` nesting. If exceeded, **justify in a comment at the section header.**

*Why.* Long sections and deep nesting are the strongest predictors of defects in maintenance. Soft target rather than hard cap because some sections (TCP receive loops) legitimately exceed it — when they do, the comment forces a moment of "is this still the cleanest shape?".

### Hygiene

#### Rule 20 — No commented-out code in committed sources
Either delete it, or wrap it in a `*` comment block with a written reason and a removal condition.

*Why.* Commented-out code rots silently and confuses every future reader. Git history is the right place for old code.

### Anti-patterns — DO NOT

| Don't | Use instead | Rule |
|---|---|---|
| `IF cond .` (period closes the IF) | `IF cond ... END-IF` | 6, 7 |
| `CALL 'WHOAMI' USING ...` (literal) | `CALL WS-WHOAMI-PGM USING ...` | 16 |
| `STRING ... EZA-ERRNO ... INTO ...` (COMP in STRING) | `MOVE EZA-ERRNO TO WS-ERRNO-D` first | 11 |
| `GO TO 9020-EXIT` | `EXIT SECTION` | 4 |
| `PERFORM 0100-FOO THRU 0100-EXIT` | `PERFORM 0100-FOO` | 2 |
| `EXEC CICS HANDLE CONDITION ...` | inline `RESP(...)` check | 12 |
| Paragraph instead of SECTION | SECTION | 1 |
| Hardcoded program name in DISPLAY / STRING | `WS-PROGRAM-NAME` populated by `WHOAMI` | — |
| Two consecutive blank lines | one blank line | 15 |
| Calling the check section unconditionally | only on the error path (IF / EVALUATE) | 13, 14 |
| `EVALUATE ... END-EVALUATE` without `WHEN OTHER` | always include `WHEN OTHER` | 10 |
| `PIC S9(9) COMP` for a plain counter | `PIC 9(9)` DISPLAY | 11 |
| Commented-out code in committed source | delete it; trust git history | 20 |

---

## 3. Standard Program Skeleton

### 3.1 Template

```cobol
      ******************************************************************
      *  NAME        : xxxxxxxx                                        *
      *  VERSION     : 1.00                                            *
      *  PURPOSE     : ...                                             *
      *                                                                *
      *  DESCRIPTION : ...                                             *
      *  CHANGES LOG :                                                 *
      *---------------------------------------------+----------+-------*
      * DESCRIPTION                                 |DATE      |NAME   *
      *---------------------------------------------+----------+-------*
      * FIRST IMPLEMENTATION                        |DD/MM/YYYY|xxx    *
      *================================================================*
       IDENTIFICATION DIVISION.
      *================================================================*
       PROGRAM-ID. xxxxxxxx.
      *================================================================*
       ENVIRONMENT DIVISION.
      *================================================================*
       CONFIGURATION SECTION.
      *----------------------------------------------------------------*
       INPUT-OUTPUT SECTION.
      *----------------------------------------------------------------*
       FILE-CONTROL.
      *================================================================*
       DATA DIVISION.
      *================================================================*
       FILE SECTION.
      *----------------------------------------------------------------*
       WORKING-STORAGE SECTION.
      *----------------------------------------------------------------*
       01 WS.
         03 WS-PROGRAM-NAME            PIC X(08) VALUE SPACES.
         03 WS-PROGRAM-VERSION         PIC X(05) VALUE '1.00'.
         03 WS-WHOAMI-PGM              PIC X(08) VALUE 'WHOAMI  '.
         03 WS-WHOAMI-BUFFER           PIC X(100) VALUE SPACES.
         03 WS-COMMAND                 PIC X(30) VALUE SPACES.
         03 WS-OBJECT                  PIC X(30) VALUE SPACES.
         03 WS-FIRST-CALL              PIC 9(01) VALUE ZERO.
           88 FIRST-CALL               VALUE ZERO.
           88 NOT-FIRST-CALL           VALUE 1.
      *----------------------------------------------------------------*
       01 ZZL-IF.
              COPY ZZLOGERC.
      *----------------------------------------------------------------*
       PROCEDURE DIVISION.
      *================================================================*
       0000-MAIN-PROGRAM SECTION.
      *----------------------------------------------------------------*
           PERFORM 0010-INITIALIZE

           PERFORM 0100-...

           PERFORM 9999-NORMAL-TERMINATION.

       0000-EXIT.
           EXIT.


      *----------------------------------------------------------------*
       0010-INITIALIZE SECTION.
      *----------------------------------------------------------------*
           IF FIRST-CALL
               SET NOT-FIRST-CALL TO TRUE

               INITIALIZE WS-WHOAMI-BUFFER

               CALL WS-WHOAMI-PGM USING WS-WHOAMI-BUFFER

               MOVE WS-WHOAMI-BUFFER(1:8) TO WS-PROGRAM-NAME

               STRING FUNCTION TRIM(WS-PROGRAM-NAME) ' ('
                      FUNCTION TRIM(WS-PROGRAM-VERSION) ') - STARTED'
                   DELIMITED BY SIZE INTO ZZL-MESSAGE
               SET ZZL-LEVEL-INFO TO TRUE

               PERFORM 9000-TRACE-HANDLING

           END-IF.

       0010-EXIT.
           EXIT.
```

### 3.2 `WS-PROGRAM-NAME` and `WS-PROGRAM-VERSION`

- `WS-PROGRAM-NAME PIC X(08) VALUE SPACES` — populated at runtime by `WHOAMI`. **Never hardcode.**
- `WS-PROGRAM-VERSION PIC X(05) VALUE '1.00'` — incremented **manually** by the developer on each modification. `WHOAMI` does not populate this.
- Always use `WS-WHOAMI-BUFFER PIC X(100)` as an intermediate for the `WHOAMI` call to avoid overwriting adjacent WS fields.

### 3.3 Trace pattern

Set `ZZL-MESSAGE`, set `ZZL-LEVEL`, then call `9000-TRACE-HANDLING`:

```cobol
           STRING
             'YOUR MESSAGE '
             FUNCTION TRIM(WS-SOME-FIELD)
             DELIMITED BY SIZE INTO ZZL-MESSAGE
           SET ZZL-LEVEL-INFO TO TRUE

           PERFORM 9000-TRACE-HANDLING
```

Message levels follow loguru convention, lowest to highest:
`TRACE` `DEBUG` `INFO` `SUCCESS` `WARNING` `ERROR` `CRITICAL`

`9000-TRACE-HANDLING` passes the raw message to `ZZLOGGER`, which builds the full output line internally: timestamp (`FUNCTION FORMATTED-CURRENT-DATE`), program name (via `WHOCALME`), level, message. The calling program never formats the output line.

Output format (built inside `ZZLOGGER`): `<datetime> <program-name> <level> <message>`

Program version is not included on every line. Include it once in the startup `INFO` message: `STRING FUNCTION TRIM(WS-PROGRAM-NAME) ' (' FUNCTION TRIM(WS-PROGRAM-VERSION) ') - STARTED' ...`

`ZZLOGGER` decides level filtering and output target (SYSOUT / CONSOLE / TDQ / TSQ / DB table). `ZZLOGGER` is designed separately.

```cobol
      *----------------------------------------------------------------*
       9000-TRACE-HANDLING SECTION.
      *----------------------------------------------------------------*
           CALL ZZL-PROGRAM USING ZZL-IF
               ON EXCEPTION
                   CONTINUE
           END-CALL

           INITIALIZE ZZL-MESSAGE
                      ZZL-LEVEL
                      ZZL-DEST.

       9000-EXIT.
           EXIT.
```

`ZZL-DEST = SPACES` means default routing (decided by `ZZLOGGER`). Set to a specific destination name before `PERFORM 9000-TRACE-HANDLING` only when a non-default destination is required.

### 3.4 Termination sections

```cobol
      *----------------------------------------------------------------*
       9998-ABNORMAL-TERMINATION SECTION.
      *----------------------------------------------------------------*
           *> Batch:  MOVE nn TO RETURN-CODE
           *> CICS:   EXEC CICS ABEND ABCODE('xxxx') ... END-EXEC
           GOBACK.
       9998-EXIT.
           EXIT.

      *----------------------------------------------------------------*
       9999-NORMAL-TERMINATION SECTION.
      *----------------------------------------------------------------*
           *> Batch:  MOVE 0 TO RETURN-CODE
           *> CICS:   EXEC CICS RETURN RESP(...) RESP2(...) END-EXEC
           GOBACK.
       9999-EXIT.
           EXIT.
```

---

## 4. Shared Utilities

### 4.1 `WHOAMI` (`common-tools/prog`)
Returns the name of the calling program.

```cobol
*  Linkage: 01 LK-PROG-NAME PIC X(100)
*  Declare: 03 WS-WHOAMI-PGM PIC X(08) VALUE 'WHOAMI  '.
CALL WS-WHOAMI-PGM USING WS-WHOAMI-BUFFER
MOVE WS-WHOAMI-BUFFER(1:8) TO WS-PROGRAM-NAME
```

### 4.2 `GJOBINFO` (`common-tools/prog`)
Returns batch job name, job number, and user ID.

```cobol
CALL WS-GJOBINFO-PGM USING RR-JOB-NAME
                           RR-JOB-NUMBER
                           RR-JOB-USER-ID
                           WS-GJOBINFO-RC
  ON EXCEPTION
    ... trace and PERFORM 9998-ABNORMAL-TERMINATION ...
END-CALL
```

### 4.3 `GENVVAR` (`common-tools/prog`)
Reads an Enterprise Server environment variable.

```cobol
01 WS-ENV-VAR-STRUCTURE.
  05 WS-ENV-VAR-NAME   PIC X(50) VALUE SPACES.
  05 WS-ENV-VAR-VALUE  PIC X(256) VALUE SPACES.
...
MOVE 'MY_VAR_NAME' TO WS-ENV-VAR-NAME
INITIALIZE WS-ENV-VAR-VALUE
*  Declare: 03 WS-GENVVAR-PGM PIC X(08) VALUE 'GENVVAR '.
CALL WS-GENVVAR-PGM USING WS-ENV-VAR-STRUCTURE
  ON EXCEPTION
    PERFORM 9998-ABNORMAL-TERMINATION
END-CALL
*  WS-ENV-VAR-VALUE = SPACES if variable is not defined
```

### 4.4 `ZFLSTTXT` (`batch-tools/prog`) — File status description
Call after any batch I/O error to get a human-readable description.

```cobol
*  Working storage:
   03 WS-ZFLSTTXT-PGM            PIC X(08) VALUE 'ZFLSTTXT'.
   03 WS-FILE-STATUS             PIC X(02) VALUE SPACES.
     88 FILE-STATUS-OK           VALUE '00'.
     88 FILE-STATUS-EOF          VALUE '10'.
   03 WS-FILE-STATUS-DESCRIPTION PIC X(100) VALUE SPACES.
...
CALL WS-ZFLSTTXT-PGM USING WS-FILE-STATUS
                           WS-FILE-STATUS-DESCRIPTION
```

### 4.5 `ZCRSPTXT` (`cics-tools/prog`) — CICS RESP description
Call after any CICS error to get a human-readable description. Reads `EIBRESP` / `EIBRESP2` directly from the EIB — no RESP parameters needed.

```cobol
*  Working storage:
   03 WS-ZCRSPTXT-PGM            PIC X(08) VALUE 'ZCRSPTXT'.
   03 WS-RESPONSE-TEXT            PIC X(200) VALUE SPACES.
*  Linkage (ZCRSPTXT PROCEDURE DIVISION):
*    DFHEIBLK                     — EIB block passed from caller
*    LK-RESPONSE-TEXT  PIC X(200) — e.g. "FUNCTION:0A04 - READQ TS  RESP:44 - QIDERR  RESP2:0"
CALL WS-ZCRSPTXT-PGM USING DFHEIBLK
                           WS-RESPONSE-TEXT
```

### 4.6 `ZEZAETXT` (`cics-tools/prog`) — EZASOKET errno description
Returns a short label for an EZA errno (the value carried in `EZA-ERRNO` and propagated to callers via `LK-EZA-ERRNO` in `TCPEZAC.cpy`). Same role as `ZCRSPTXT`, applied to TCP/IP socket errnos.

```cobol
*  Working storage:
   03 WS-ZEZAETXT-PGM    PIC X(08) VALUE 'ZEZAETXT'.
   03 WS-EZA-ERRNO-TEXT  PIC X(32) VALUE SPACES.
*  Linkage:
*    01 LK-EZA-ERRNO   PIC S9(09) COMP   (IN)
*    01 LK-ERRNO-TEXT  PIC X(32)         (OUT)
CALL WS-ZEZAETXT-PGM USING LK-EZA-ERRNO
                           WS-EZA-ERRNO-TEXT
*  Then trim when displaying / STRINGing:
STRING 'OPEN FAILED RC=' WS-EZA-RC-D
       ' ERRNO=' WS-EZA-ERRNO-D
       ' (' FUNCTION TRIM(WS-EZA-ERRNO-TEXT) ')'
    DELIMITED BY SIZE INTO ZZL-MESSAGE
```

The output buffer is sized `PIC X(32)` to allow longer labels if needed; always `FUNCTION TRIM` it when displaying. Full errno table in §A.3.

### 4.7 Batch-to-CICS bridge

- **`JCLBCICS`** (`common-tools/prog`) — batch, reads CICS commands from SYSIN, calls `JCLSCICS` via DPL.
- **`JCLSCICS`** (`common-tools/prog`) — CICS server, executes commands from COMMAREA.
- **`JCLCICSC`** (`common-tools/copy`) — shared COMMAREA (100-command array with RESP/RESP2).
- Retry count: `JCLBCICS_TRY_COUNT` ES environment variable.
- Response checking: `JCLBCICS_CICS_RC=ASIS` to check RESP values, otherwise ignore.

---

## 5. Batch Programs

Patterns specific to batch COBOL.

### 5.1 File status handling — `9020-CHECK-FILE-STATUS`

Bracket every I/O operation with an action label before and a check `PERFORM` after:

```cobol
           MOVE 'READ FILE'           TO WS-COMMAND
           MOVE 'MY-FILE'             TO WS-OBJECT
           READ my-file INTO ws-record
           PERFORM 9020-CHECK-FILE-STATUS
```

Standard `9020-CHECK-FILE-STATUS` section template:

```cobol
      *----------------------------------------------------------------*
       9020-CHECK-FILE-STATUS SECTION.
      *----------------------------------------------------------------*
           EVALUATE TRUE
             WHEN FILE-STATUS-OK
               CONTINUE
             WHEN FILE-STATUS-EOF

               EXIT SECTION

             WHEN OTHER

               CALL WS-ZFLSTTXT-PGM USING WS-FILE-STATUS
                                          WS-FILE-STATUS-DESCRIPTION

               STRING FUNCTION TRIM(WS-COMMAND) ' '
                      FUNCTION TRIM(WS-OBJECT) ' STATUS='
                      FUNCTION TRIM(WS-FILE-STATUS-DESCRIPTION)
                   DELIMITED BY SIZE INTO ZZL-MESSAGE
               SET ZZL-LEVEL-ERROR TO TRUE

               PERFORM 9000-TRACE-HANDLING

               PERFORM 9998-ABNORMAL-TERMINATION

           END-EVALUATE.

       9020-EXIT.
           EXIT.
```

### 5.2 SSTMJCL convention (DEV only)

DD statements in `SSTMJCL` JCL are accessible from CICS programs as standard COBOL batch sequential files. Specific to the Rocket Enterprise Server emulation — **not** valid on real z/OS. Use only where the program is known to run under DEV.

---

## 6. CICS Programs

Patterns specific to CICS COBOL.

### 6.1 Response handling pattern

Standard working storage:

```cobol
       01 WS-CICS-RESPONSE.
         03 WS-ZCRSPTXT-PGM          PIC X(08) VALUE 'ZCRSPTXT'.
         03 WS-RESPONSE              PIC S9(08) COMP VALUE ZERO.
         03 WS-RESPONSE-2            PIC S9(08) COMP VALUE ZERO.
         03 WS-RESPONSE-TEXT         PIC X(200) VALUE SPACES.
```

`WS-RESPONSE` and `WS-RESPONSE-2` are `COMP` because RESP / RESP2 are system interface fields (Rule 11 — required COMP).

Bracket every `EXEC CICS` command with an action label before and an inline `IF` or `EVALUATE` after (Rule 13). Never call the check section unconditionally — it handles only the unexpected error path.

For a single expected response use `IF`:

```cobol
           MOVE 'WRITEQ TS'          TO WS-COMMAND
           MOVE 'LOG-TSQ'            TO WS-OBJECT
           EXEC CICS WRITEQ TS QUEUE(LOG-TSQ) ...
               RESP(WS-RESPONSE)
               RESP2(WS-RESPONSE-2)
           END-EXEC
           IF WS-RESPONSE = DFHRESP(NORMAL)
               CONTINUE
           ELSE
               PERFORM 9010-CHECK-CICS-RESPONSE
           END-IF
```

For multiple expected responses use `EVALUATE`:

```cobol
           MOVE 'READQ TS'           TO WS-COMMAND
           MOVE 'TNDMSTTS'           TO WS-OBJECT
           EXEC CICS READQ TS QUEUE(TNDMSTTS) INTO(WS-REC)
               ITEM(EHAD)
               RESP(WS-RESPONSE)
               RESP2(WS-RESPONSE-2)
           END-EXEC
           EVALUATE WS-RESPONSE
               WHEN DFHRESP(NORMAL)
                   *> process data
               WHEN DFHRESP(QIDERR)
                   *> handle no-data — not an error
               WHEN OTHER
                   PERFORM 9010-CHECK-CICS-RESPONSE
           END-EVALUATE
```

`WHEN OTHER` is mandatory (Rule 10).

Standard `9010-CHECK-CICS-RESPONSE` section template:

```cobol
      *----------------------------------------------------------------*
       9010-CHECK-CICS-RESPONSE SECTION.
      *----------------------------------------------------------------*
           IF WS-RESPONSE NOT EQUAL ZERO

               CALL WS-ZCRSPTXT-PGM USING DFHEIBLK
                                          WS-RESPONSE-TEXT

               STRING FUNCTION TRIM(WS-COMMAND) ' '
                      FUNCTION TRIM(WS-OBJECT) ': '
                      FUNCTION TRIM(WS-RESPONSE-TEXT)
                   DELIMITED BY SIZE INTO ZZL-MESSAGE
               SET ZZL-LEVEL-ERROR TO TRUE

               PERFORM 9000-TRACE-HANDLING

               PERFORM 9998-ABNORMAL-TERMINATION

           END-IF.

       9010-EXIT.
           EXIT.
```

### 6.2 EIB addressability — exception to Rule 12

`EXEC CICS ADDRESS EIB` must be issued **bare** — no `RESP` or `RESP2`. CICS writes RESP into EIB fields, but EIB is not addressable until this call completes; adding `RESP` causes an abend.

```cobol
           EXEC CICS ADDRESS EIB(EIB-BLOCK-ADDR)
           END-EXEC

           SET ADDRESS OF DFHEIBLK TO EIB-BLOCK-ADDR
```

This is the **only** `EXEC CICS` command exempt from Rule 12.

### 6.3 EZASOKET interface (CICS TCP/IP)

All TCP socket operations go through `CALL 'EZASOKET'` via the `BSTTEZA` / `BSTTEZAC` copybooks in `cics-tools/copy/`.

Working storage declaration:

```cobol
       01 EZA-WORK.
              COPY BSTTEZA.
              COPY BSTTEZAC.
```

Key fields from `BSTTEZA` (all system interface fields — required `COMP` per Rule 11):

| Field | Type | Purpose |
|---|---|---|
| `EZA-FUNCTION` | PIC X(16) | Function name |
| `EZA-S` | PIC S9(04) COMP | Socket descriptor |
| `EZA-ERRNO` | PIC S9(09) COMP | Error number |
| `EZA-RETCODE` | PIC S9(08) COMP | Return code (< 0 = error) |
| `EZA-AF` | PIC S9(09) COMP VALUE +2 | Address family (2 = IPv4) |
| `EZA-SOCTYPE` | PIC S9(09) COMP VALUE +1 | Socket type (1 = TCP stream) |
| `EZA-FLAGS` | PIC S9(09) COMP | SEND / RECV flags (0 = none) |
| `EZA-NBYTE` | PIC S9(09) COMP | Byte count |
| `EZA-NAME-FAMILY` | PIC S9(04) COMP | Address family in socket address |
| `EZA-NAME-PORT` | PIC 9(04) COMP | Port number |
| `EZA-NAME-IPADDRESS` | PIC X(04) | Binary IPv4 address |
| `EZA-IDENT-TAG` | PIC X(06) | Always `'SOCKET'` for INITAPI |
| `EZA-IDENT-SYSID` | PIC X(02) | TCP/IP stack ID (`'01'`) |

Call sequences:

```cobol
*  INITAPI
MOVE 'INITAPI' TO EZA-FUNCTION
MOVE +0        TO EZA-MAXSOC
MOVE 'SOCKET'  TO EZA-IDENT-TAG
MOVE STACK-ID  TO EZA-IDENT-SYSID
MOVE SPACES    TO EZA-SUBTASK
MOVE +0        TO EZA-MAXSNO
CALL 'EZASOKET' USING EZA-FUNCTION EZA-MAXSOC EZA-IDENT
                      EZA-SUBTASK EZA-MAXSNO EZA-ERRNO EZA-RETCODE

*  SOCKET — move EZA-RETCODE to EZA-S on success
MOVE 'SOCKET' TO EZA-FUNCTION
CALL 'EZASOKET' USING EZA-FUNCTION EZA-AF EZA-SOCTYPE
                      EZA-PROTO EZA-ERRNO EZA-RETCODE

*  CONNECT
MOVE 'CONNECT'   TO EZA-FUNCTION
MOVE LOW-VALUES  TO EZA-NAME
MOVE +2          TO EZA-NAME-FAMILY
MOVE PORT-NUMBER TO EZA-NAME-PORT
MOVE IP-ADDRESS  TO EZA-NAME-IPADDRESS
CALL 'EZASOKET' USING EZA-FUNCTION EZA-S EZA-NAME EZA-ERRNO EZA-RETCODE

*  RECV
MOVE 'RECV' TO EZA-FUNCTION
MOVE +0     TO EZA-FLAGS
MOVE BYTES-WANTED TO EZA-NBYTE
CALL 'EZASOKET' USING EZA-FUNCTION EZA-S EZA-FLAGS
                      EZA-NBYTE DATA-BUFFER EZA-ERRNO EZA-RETCODE

*  SEND
MOVE 'SEND' TO EZA-FUNCTION
MOVE +0     TO EZA-FLAGS
MOVE BYTES-TO-SEND TO EZA-NBYTE
CALL 'EZASOKET' USING EZA-FUNCTION EZA-S EZA-FLAGS
                      EZA-NBYTE DATA-BUFFER EZA-ERRNO EZA-RETCODE

*  CLOSE
MOVE 'CLOSE' TO EZA-FUNCTION
CALL 'EZASOKET' USING EZA-FUNCTION EZA-S EZA-ERRNO EZA-RETCODE

*  TERMAPI
MOVE 'TERMAPI' TO EZA-FUNCTION
CALL 'EZASOKET' USING EZA-FUNCTION
```

**`EZA-RETCODE` vs `EZA-OK` — internal vs external test.** `EZA-OK` is an 88-level on `LK-EZA-RETURN-CODE`; that field is the contract with the caller of the wrapping module (e.g. `TCPCLNT` calling `TCPEZA`). Inside the wrapper, test `EZA-RETCODE NOT < ZERO` directly — it's the local result of each `EZASOKET` call. Using `EZA-OK` for the internal check tests the wrong field, and for `SOCKET`/`RECV` (which return positive values on success) wouldn't satisfy `=ZERO` even if the field were populated.

```cobol
CALL 'EZASOKET' USING ...
IF EZA-RETCODE NOT < ZERO
    <success path>
ELSE

    PERFORM 9020-CHECK-EZA-RESPONSE

    EXIT SECTION

END-IF
```

`EZA-ERRNO = 35` on a non-blocking `RECV` = "no data available" — not an error. The retry loop tests for it via the 88-level `EZA-NO-DATA` (on `LK-EZA-ERRNO`).

Standard `9020-CHECK-EZA-RESPONSE` section (mirror of `9010` for the EZA path):

```cobol
      *----------------------------------------------------------------*
       9020-CHECK-EZA-RESPONSE SECTION.
      *----------------------------------------------------------------*
           MOVE EZA-ERRNO   TO WS-ERRNO-D
           MOVE EZA-RETCODE TO WS-RETCODE-D

           CALL WS-ZEZAETXT-PGM USING EZA-ERRNO WS-ERRNO-TEXT

           STRING FUNCTION TRIM(WS-COMMAND) ' '
                  FUNCTION TRIM(WS-OBJECT) ': RC=' WS-RETCODE-D
                  ' ERRNO=' WS-ERRNO-D
                  ' (' FUNCTION TRIM(WS-ERRNO-TEXT) ')'
               DELIMITED BY SIZE INTO ZZL-MESSAGE
           SET ZZL-LEVEL-ERROR TO TRUE

           PERFORM 9000-TRACE-HANDLING

           MOVE -1 TO LK-EZA-RETURN-CODE.

       9020-EXIT.
           EXIT.
```

Display sidecars for `EZA-*` fields in trace messages:

```cobol
       01 WS-TRACE-DISPLAY.
         03 WS-ERRNO-D     PIC 9(09).    *> errno always >= 0
         03 WS-RETCODE-D   PIC -9(08).   *> can be -1
         03 WS-PORT-D      PIC 9(04).    *> always >= 0
         03 WS-ERRNO-TEXT  PIC X(32).
```

FCNTL — set non-blocking mode:

```cobol
01 WS-FCNTL-COMMAND  PIC 9(8) BINARY VALUE 4.
01 WS-FCNTL-REQARG   PIC 9(8) BINARY VALUE 4.
...
MOVE 'FCNTL' TO EZA-FUNCTION
CALL 'EZASOKET' USING EZA-FUNCTION EZA-S
                      WS-FCNTL-COMMAND WS-FCNTL-REQARG
                      EZA-ERRNO EZA-RETCODE
```

### 6.4 BMS map workflow

The two-environment build means BMS maps are authored locally and assembled remotely. The folder convention:

| Folder | Contents | Authored where |
|---|---|---|
| `cics-tools/bms/` | `.bms` map source files (hand-authored) | Local |
| `cics-tools/copy/` | `.cpy` symbolic maps generated by the Rocket BMS compiler | Remote, then transferred back |

**Author rule for `.bms` files.** Comment lines must end at column 71 or earlier. Any non-blank character at column 72 — even inside a `*` comment — is read as a continuation marker by the Rocket BMS assembler and silently masks the next macro line. Past incident: a comment line was exactly 72 chars long and the trailing `)` masked the following `DFHMSD` macro.

Build flow:

1. Edit `cics-tools/bms/<MAPSET>.bms` locally.
2. Transfer to the remote VS2022 / Enterprise Developer project.
3. Import into the project.
4. Set the `.bms` properties — generated copybook name (convention: same base as the consumer program, e.g. `TCPTDRM.bms` → `TCPTDRC.cpy`).
5. Build remotely. BMS compiler produces the `.cpy`.
6. Transfer the `.cpy` back, import into `cics-tools/copy/`.
7. Compile the consuming program — picks up the symbolic map via `COPY <name>`.

Generated copybook shape (output map, `MODE=OUT`, `TIOAPFX=YES`):

```cobol
   01 <MAPNAME>O.
      03 FILLER          PIC X(12).      *> TIOA prefix
      03 FILLER          PIC X(2).       *> length filler per field
      03 L01A            PIC X.          *> attribute byte
      03 L01O            PIC X(79).      *> output data
      03 FILLER          PIC X(2).
      03 L02A            PIC X.
      03 L02O            PIC X(79).
      ... 24 (or N) repetitions, one per DFHMDF
```

Consuming pattern in the COBOL program:

```cobol
       COPY TCPTDRC.
       ...
       MOVE 'something' TO L01O
       STRING 'foo' bar DELIMITED BY SIZE INTO L02O
       ...
       EXEC CICS SEND MAP('TCPTDRM') FROM(TCPTDRMO)
           ERASE FREEKB
           RESP(WS-RESPONSE) RESP2(WS-RESPONSE-2)
       END-EXEC
```

### 6.5 Pseudo-conversational display pattern

For a CICS transaction that displays a screen and waits for the user to dismiss it, do NOT use `EXEC CICS RECEIVE` inside the transaction. `RECEIVE` picks up the AID key that started the transaction (the ENTER from typing the trans-ID), returns immediately without waiting, and if the program reacts with `RETURN TRANSID(...)` you get a restart loop that flashes the screen.

The bulletproof pattern is pseudo-conversational with a COMMAREA flag:

```cobol
       0000-MAIN-PROGRAM SECTION.

           EVALUATE TRUE
               WHEN EIBCALEN > 0 AND EIBAID NOT = DFHENTER

                   PERFORM 9999-NORMAL-TERMINATION    *> dismiss

               WHEN OTHER

                   PERFORM 0010-INITIALIZE
                   PERFORM 0020-MAIN-LOGIC            *> work + SEND PAGE
                   PERFORM 9990-RETURN-CONVERSATIONAL *> re-arm trans

           END-EVALUATE.
```

The re-arm section:

```cobol
       9990-RETURN-CONVERSATIONAL SECTION.
           EXEC CICS RETURN TRANSID(EIBTRNID)
                            COMMAREA(WS-COMMAREA-FLAG)
               RESP(WS-RESPONSE) RESP2(WS-RESPONSE-2)
           END-EXEC
           IF WS-RESPONSE = DFHRESP(NORMAL)
               CONTINUE
           ELSE
               PERFORM 9010-CHECK-CICS-RESPONSE
           END-IF
           GOBACK.
```

Where `WS-COMMAREA-FLAG PIC X(01) VALUE 'X'`. The value is irrelevant; only the presence (`EIBCALEN > 0` on re-entry) matters.

Branch matrix:

| `EIBCALEN` | `EIBAID` | Branch | Effect |
|---|---|---|---|
| 0 | DFHENTER | run+wait | First call (user typed trans) |
| > 0 | DFHENTER | run+wait | Press ENTER → run another cycle |
| > 0 | any other | dismiss | CLEAR/PF* → end transaction |

Why it works:
- Task ends with `RETURN TRANSID` → BMS-delivered page stays on screen.
- Any AID key re-invokes the same trans with `EIBCALEN > 0`.
- Dispatch on `EIBAID` lets you treat ENTER as "rerun" and everything else as "exit" without dragging in an explicit `RECEIVE`.

Requires `COPY DFHAID` in WORKING-STORAGE for the AID-key constants.

### 6.6 ASCII/EBCDIC translation — `A2ERAFI`

For CICS TCP programs exchanging data with ASCII peers:

```cobol
01 A2E-COMMAREA.
  05 TRANS-DIR    PIC X.       *> 'A' = ASCII -> EBCDIC,  'E' = EBCDIC -> ASCII
  05 RET-CODE     PIC X(2).    *> 'OK' or 'ER'
  05 A2E-LENGTH   PIC S9(4) COMP.
  05 A2E-STRING   PIC X(2048).

CALL 'A2ERAFI' USING A2E-COMMAREA
```

`A2E-LENGTH` is `COMP` (system interface field).

---

## 7. Tooling

### 7.1 `cobol-format` skill

Apply three-pass formatting to `.cob` and `.cpy` files. Persistent script at `.claude/skills/cobol-format/cobol_fmt.py`.

**Pass 1 — Remove all empty lines.** Strip every blank or whitespace-only line.

**Pass 2 — Blank lines around control-flow statements.** Surround each of these with one blank line before and one after:

- Standalone `PERFORM` (e.g. `PERFORM 9000-TRACE-HANDLING`).
- Block `PERFORM` (`VARYING`, `WITH TEST`, `UNTIL`, `TIMES`) — blank before `PERFORM`, blank after matching `END-PERFORM`.
- `CALL … END-CALL` — blank before `CALL`, blank after `END-CALL`.
- `CALL` without `END-CALL` — blank before `CALL`, blank after the last continuation line.
- `EXEC … END-EXEC` — blank before `EXEC`, blank after `END-EXEC`.
- `EXIT SECTION` and `EXIT PERFORM` — blank before, blank after. (NOT the plain `EXIT.` that follows a section's `nnnn-EXIT.` label.)

Never insert duplicate blank lines.

**Recurse into block bodies.** Nested control-flow inside a block `PERFORM` (and inside `IF` / `EVALUATE` within them) must also get its blank lines.

**Pass 3 — Two blank lines before opening section dividers.** A section divider is a comment line at col 7 (`*`) with ≥ 5 dashes (`-`) and no `+` (lines with `+` are change-log table borders — never touched).

- Divider preceded (ignoring blanks) by a section/paragraph name → **closing** divider, leave alone.
- Divider preceded by one-or-more `*` comment lines that are themselves preceded by another divider → **closing** (the multi-line WS-comment-block header pattern), leave alone.
- All others → **opening** divider, ensure exactly 2 blank lines before it.

Invoke:

```
python "%CLAUDE_PROJECT_DIR%/.claude/skills/cobol-format/cobol_fmt.py" <file1> [<file2> ...]
```

Output: `name: before -> after lines` per file. If a bug is found, fix the script in place — do not rewrite.

### 7.2 Documentation reference

Full Rocket Enterprise Developer 11.0 PU04 documentation is available locally as ~20,250 searchable HTML topic files:

```
C:\Users\vladimir.g\Documents\Library\MicroFocus\ED11_PU04_HELP\RocketEnterpriseDeveloper\
```

Each file is one help topic (DITA-OT XHTML format). The title is in `<meta name="DC.title">`. Grep titles to locate a topic, then read the file.

Covers: COBOL language reference, compiler directives, CICS API, Enterprise Server, z/VSE runtime.

---

## Appendix

### A.1 Reserved section prefixes

| Prefix | Section | Returns? |
|---|---|---|
| `0000` | `MAIN-PROGRAM` | yes |
| `0010` | `INITIALIZE` | yes |
| `01xx`–`89xx` | Functional sections | yes |
| `9000` | `TRACE-HANDLING` | yes |
| `9010` | `CHECK-CICS-RESPONSE` | yes (may PERFORM 9998) |
| `9020` | `CHECK-FILE-STATUS` / `CHECK-EZA-RESPONSE` | yes (may PERFORM 9998) |
| `9990` | `RETURN-CONVERSATIONAL` | no (GOBACK) |
| `9998` | `ABNORMAL-TERMINATION` | **no** (GOBACK) |
| `9999` | `NORMAL-TERMINATION` | no (GOBACK) |

### A.2 PIC patterns

| Use | PIC | Notes |
|---|---|---|
| Flag / counter / unsigned value | `PIC 9(n)` | Default — no `S`, no editing |
| Signed counter (rare) | `PIC S9(n) SIGN IS LEADING SEPARATE` | Avoids overpunched last digit in dumps |
| Display sidecar — always ≥ 0 | `PIC 9(n)` | e.g. `WS-ERRNO-D PIC 9(09)` |
| Display sidecar — can be negative | `PIC -9(n)` | Editing picture; prints `-` or space. e.g. `WS-RETCODE-D PIC -9(08)` |
| System interface field | `PIC S9(n) COMP` | Required for EZA-\*, EIB, RESP/RESP2, DFH\* |
| Pointer / address | `POINTER` | e.g. `EIB-BLOCK-ADDR POINTER VALUE NULL` |
| FCNTL binary constant | `PIC 9(8) BINARY` | EZASOKET requires this form |

### A.3 EZASOKET errno labels (via `ZEZAETXT`)

Single source of truth for errno → label is `ZEZAETXT.cob`. Extend there and the new label is picked up by every caller automatically.

| Errno | Label |
|---|---|
| 32 | `BROKEN-PIPE` |
| 35 | `NO-DATA` |
| 50 | `NET-DOWN` |
| 51 | `NET-UNREACH` |
| 53 | `CONN-ABORTED` |
| 54 | `CONN-RESET` |
| 57 | `NOT-CONNECTED` |
| 60 | `TIMED-OUT` |
| 61 | `CONN-REFUSED` |
| 64 | `HOST-DOWN` |
| 65 | `HOST-UNREACH` |
| other | `UNKNOWN` |

Always `FUNCTION TRIM` the output buffer (`PIC X(32)`) when displaying or `STRING`-ing.
