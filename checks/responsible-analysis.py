"""Check 31: the responsible analysis thread is still whole.

Thirteen commitments run through the playbook on what an analyst owes the people their analysis
affects. They are scattered on purpose: each sits in the section where the question arises, so a
reader deciding a level meets the ones that belong there and a reader writing up meets different
ones. Nobody opening the playbook sees them as a set, which is right for a reader and a hazard for
the document, because no single page looks wrong when one of them is edited away.

So they are listed here instead, each by the words it turns on. The phrases are the load-bearing
ones rather than whole sentences: the wording can be improved without failing this, but the claim
cannot be dropped. Where a commitment is a quotation from a standard, the quotation itself is the
phrase, because that is the part which must not drift into a looser paraphrase. The comment on
each row says what the row protects, so that changing one is a deliberate act.

Two of these matter more than their length suggests. The scope of the Algorithmic Transparency
Recording Standard is quoted rather than summarised, in two steps, because a paraphrase that reads
broader than the standard would commit NHSBSA to records the standard does not ask for. And the
three prompts beside the decision sheet are written so that none of them raises an assurance
level: they prompt a thought, and letting them harden into triggers would change what the playbook
asks of every piece of work.

Hard wraps are normalised before searching. The sources are wrapped at 100 characters, so a phrase
can straddle a line break and be present on the page while absent from the raw text.
"""
import pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PB = ROOT / 'guidance'

# (commitment, section or None for anywhere, [phrases that carry it])
POINTS = [
    # The standard's own scope test, in its own words. A summary of it reads broader than it
    # is, and a playbook that overstates the scope commits NHSBSA to records nobody asked for.
    ('ATRS scope is the standard\'s, not a broader reading', '09-resources', [
        'significant influence on a decision-making process with public effect',
        'directly interact with the general public',
        'not where a tool is an analytical model supporting broad government policymaking']),

    # The transparency question and the assurance level are settled by different things.
    # Collapsing them turns a Level 4 score into a record, and lets a Level 2 tool escape one.
    ('The ATRS decision is separate from the assurance level', '09-resources', [
        'The two decisions are separate',
        'it is not the assurance level it scored',
        'Make the check at scoping']),

    # The two roles the standard names, and the sentence marking NHSBSA's own route as a
    # proposal. Presenting a local arrangement as a requirement of the standard is the error.
    ('ATRS ownership is named as a governance decision', '09-resources', [
        'single point of contact',
        'senior responsible owner',
        'governance decision rather than something the standard settles',
        'That is a proposal, not']),

    # An ethical concern with no record of what was decided is indistinguishable, a year
    # later, from one nobody noticed. Six fields are what make it an audit trail.
    ('An ethical concern has six fields to record', '09-resources', [
        'Record six things',
        'Who is touched by this, in the data and beyond it',
        'a harm recorded without the benefit beside it',
        'What you actually changed',
        'What is still there after the mitigations',
        'The role that accepted that residual risk',
        'Where it went, if the analyst and the commissioner could not settle it']),

    # "Have you looked at fairness?" is unanswerable. These five turn it into something a
    # person can answer and an assurer can check.
    ('Fairness is five answerable questions', '09-resources', [
        'who is **represented** in the data, and in what proportion',
        'who is **missing** from it altogether',
        'acting as a **proxy** for a protected or sensitive characteristic',
        # Not 'whether outcomes differ': the five were rewritten as five questions, which is
        # what this assertion is named for. The clause is what has to be there, not the
        # conjunction that used to introduce it.
        '**outcomes differ** across groups once you look',
        'how much fairness work is **proportionate** to what this analysis decides']),

    # "A human is involved" can be true while nobody is in a position to change anything.
    # These five questions are the difference between oversight and the appearance of it.
    ('Meaningful human oversight is defined, not asserted', '09-resources', [
        'Who reviews the output', 'What authority do they have',
        'When can they challenge or override', 'What gets recorded',
        'Can the decision be reviewed or appealed']),

    # What changes about an analyst's accountability when a tool helps them work: nothing.
    # Saying so plainly beats leaving it to be worked out one analyst at a time.
    ('Using AI tools to do the analysis', '09-resources', [
        'Use the tools your organisation has approved',
        'Do not put data into a tool that is not cleared to hold it',
        'Verify what comes back',
        'Accountability does not transfer',
        'Record material use where it affects reproducibility']),

    # Identifying an ethical concern without naming where it goes leaves it with the person
    # least able to settle it.
    ('The ethical escalation route is named', '09-resources', [
        'Where an ethical concern goes if it is not settled',
        'Analytical Quality and Assurance Lead',
        'Refusing to do a piece of analysis is a legitimate outcome']),

    # The questions that are cheap to ask at scoping and expensive to discover at publication.
    ('Responsible analysis questions at scoping', '01-engagement-and-scoping', [
        'Five questions worth asking before you start',
        'Who could be affected by that decision',
        'under-represented in, or missing from, the data',
        'What happens if the analysis is wrong',
        'Is there an algorithmic tool in this']),

    # A gap in coverage is not only a wider interval. It is a group the analysis cannot see.
    ('Data quality is tied to fairness, not only to uncertainty', '07-deciding-your-assurance-level', [
        'Including who is missing from it',
        'blind spot in the conclusion',
        'affecting one group differently']),

    # Three prompts that catch work where the score alone is not the whole of the risk. The
    # last phrase carries as much as the others: none of them raises the level by itself.
    ('Three prompts beside the decision sheet that do not move the level',
     '07-deciding-your-assurance-level', [
        'Three prompts that do not change the level',
        'algorithmic or machine learning tool doing part of the work',
        'influence the same kind of decision repeatedly',
        'Could any group be affected differently',
        'None of them raises the level by itself']),

    # The two limitations easiest to leave out of a write-up, and the two most likely to
    # mislead the person who acts on it.
    ('Communicating findings names who is not in the data', '04-delivery-and-sign-off', [
        'Who is not in the data', 'How this could be misread']),

    # Reuse is the change most likely to invalidate assurance that was sound for the original
    # question. Four things to check, and all four have to be named.
    ('Reuse asks what has changed since the original was assured',
     '05-review', [
        'Before any reuse, four things are worth checking',
        'the analysis covers changed, or is the new use about a different one',
        'moved in coverage, definition or quality since',
        'one the method was built to answer',
        'shifted, so that the same output now carries more weight']),
]


def flat(path):
    return re.sub(r'\s+', ' ', path.read_text(encoding='utf-8'))


INCLUDE = re.compile(r'\{\{<\s*include\s+(\S+?)\s*>\}\}')


def text_for(section):
    """Everything a reader of that section reads, partials followed.

    A point can be answered inside an included partial, and a reader meets a partial as part of
    the page rather than as a separate document.
    """
    root = PB / section
    if not root.is_dir():
        return None
    seen, out, stack = set(), [], sorted(root.glob('*.qmd'))
    while stack:
        p = stack.pop()
        if p in seen or not p.exists():
            continue
        seen.add(p)
        raw = p.read_text(encoding='utf-8')
        out.append(raw)
        for inc in INCLUDE.findall(raw):
            stack.append(PB.parent / inc.lstrip('/').replace('guidance/', 'guidance/', 1)
                         if inc.startswith('/') else p.parent / inc)
    return re.sub(r'\s+', ' ', '\n'.join(out))


EVERYTHING = re.sub(r'\s+', ' ', '\n'.join(
    p.read_text(encoding='utf-8') for p in sorted(PB.rglob('*.qmd'))))

fail = []
for point, section, phrases in POINTS:
    hay = EVERYTHING if section is None else text_for(section)
    if hay is None:
        fail.append('%s: section %s is not in the playbook' % (point, section))
        continue
    missing = [f for f in phrases if f.lower() not in hay.lower()]
    where = section or 'the playbook'
    if missing:
        fail.append('%s: %s no longer says %s'
                    % (point, where, ', '.join('"%s"' % m for m in missing)))
    else:
        print('  ok   %-58s %d phrase(s) in %s' % (point, len(phrases), where))

print()
if fail:
    print('FAIL: %d commitment(s) no longer carried by the playbook' % len(fail))
    for f in fail:
        print('  X   %s' % f)
    raise SystemExit(1)
print('PASS: all %d responsible analysis commitments intact, %d phrases checked'
      % (len(POINTS), sum(len(p) for _, _, p in POINTS)))
