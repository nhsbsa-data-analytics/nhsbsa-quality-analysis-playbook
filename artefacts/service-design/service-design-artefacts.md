# Service design artefacts for the playbook

Eleven boards covering the journeys through the NHSBSA Producing Quality Analysis Playbook, one
piece of work at each assurance level, the grid the whole playbook is organised on, the service
the playbook describes and the playbook site itself. They are made to be worked on rather
than read: put on a wall, argued with, moved about, and marked up.

Each one comes in two forms in this folder. A `.drawio` file, which is the drawn artefact with its
lanes, lines and arrows already in place, and a sheet in `miro-paste-grids.xlsx`, which is the same
content laid out in the shape of the board so that it can be pasted straight into Miro as sticky
notes. `png/` holds a picture of each one for anybody who only wants to look, and a `.svg` of the same
drawing beside it. The Word and PDF copies of this note end with every board written out as text,
in the order a reader of the picture would meet it, for anybody who cannot see the picture. The
`.svg` of each board carries the same words as its description.

Which file to use depends on where the board is going. The `.svg` files are for web browsers: each
label in one is web page content drawn inside the picture, so a browser shows the whole board, and
a program that is not a browser, such as an image editor, a word processor or presentation
software, may show the boxes and lines without their words. The `.png` files are the portable
pictures, so use those to place a board in a document or a slide. The `.drawio` files are the
editable sources, and the place to change a board.

## What the eleven are

| File | What it is | What it is for |
|------------------------------------|-------------------------|----------------------------------------|
| `01-journey-analyst` | Journey map, nine stops | The analyst's route through the playbook, from the question they were handed to the lesson that reaches the next piece of work |
| `02-journey-commissioner` | Journey map, seven stops | The commissioner's route, from the decision they need to make to whether the analysis did any good |
| `03-journey-critical-friend` | Journey map, seven stops | One assignment, from being asked to saying what was assured |
| `04-journey-sro` | Journey map, seven stops | One Business Critical output, from being named to revalidating the designation |
| `05-handoffs-level-1-exploratory-analysis` | Handoff map | Exploratory analysis at Level 1 Standard, with the handoffs between the roles drawn and numbered |
| `06-handoffs-level-2-operational-dashboard` | Handoff map | A monthly operational dashboard at Level 2 Enhanced |
| `07-handoffs-level-3-official-statistics` | Handoff map | An official statistics publication at Level 3 Comprehensive |
| `08-handoffs-level-4-funding-formula` | Handoff map | A funding allocation formula at Level 4 Business Critical |
| `09-phases-and-roles` | Grid | Five phases across, four roles down, and one line in each of the twenty cells. The shape the playbook itself is organised on |
| `10-blueprint-assurance-service` | Service blueprint | The service the playbook describes: who does what at each stage, and which of it the commissioner sees |
| `11-blueprint-playbook-site` | Service blueprint | The site: what a reader meets, what it does behind that, and what keeps it true after handover |

The four journey maps share a shape. Stops run across the top in the order they are met. Underneath
each stop sit four lanes: the section of the playbook that answers it, what you do there, the
outputs, and what the playbook warns about at that stop. **Read the "Outputs" lane on its own and it
is the evidence trail for one piece of analysis.**

**The four handoff maps are one board per assurance level**, each drawing the worked example
NHSBSA's own Analytical Assurance Decision Tool gives for that level. They share the grid's shape,
with the handoffs drawn on top, because what a workshop argues about is who is waiting on whom.
Read side by side they answer the question no single page of the playbook answers in one picture:
what changes when the level changes. Three things grow with it.

**The cast.** Nobody signs a Level 1 off beyond the analyst, so the fourth lane on that board is
empty at four of its five stages, which is the point of the board rather than an omission. A team
lead signs Level 2. The Lead Official for Statistics signs Level 3. At Level 4 a Lead Assurer signs
before the Analysis Senior Responsible Officer approves.

**The distance of the reviewer.** A colleague within your team, then somebody who had no hand in
the work, then an assurer from outside the delivering team, then a Lead Assurer with external
review as well.

**The finish line.** Stored with the output, then archived and linked from it, then published with
the quality assurance statement, then published, on the register and revalidated annually.

The tool's annex of worked examples is marked as still to be developed, so each board says on its
face that it is the route this playbook sets out for work of that kind rather than a record of a
particular piece of work. Score your own work rather than match it to the nearest board.

The two blueprints share a different shape, and it is the standard one. Stages run across. Lanes
run down, and three rules separate them. The line of interaction separates what the customer of the
service does from what is done for them. The line of visibility separates work they see from work
they do not. The line of internal interaction separates this piece of work from the roles that
stand behind all of it.

**The grid uses the blueprint shape without the three rules**, because nothing in it is hidden from
anybody: five phases across, four roles down, and one line in each cell. It is the one to put on
the wall first in a session about the playbook as a whole, because a row is one role's whole piece
of work and a column is one moment with everybody in it.

## Three ways to get these into Miro

**Pasting a grid is the quickest, and it is the one to use for a working session.** Open
`miro-paste-grids.xlsx`, go to the sheet you want, select the block that starts at the stage row and
includes the first column of lane names, copy it, then paste onto a Miro board. Every filled cell
becomes one sticky note and the stickies keep the row and column they had in the sheet, so the board
comes out in the shape of the artefact. An empty cell makes no sticky, so a stage where a role has
nothing to do stays empty. Miro's limit for one paste is 5,000 cells across at most 50 rows and 100
columns, and the largest block here is sixty cells.

What this route does not bring is the lines, the arrows and the colours. The three blueprint lines
arrive as one sticky each, to be stretched across the board or replaced with a line. The handoff
arrows and the loop are in the notes under each block rather than on the board. For a session where
people are going to move things anyway, that is usually the right trade.

**Importing the drawing keeps the layout.** Open a `.drawio` file at diagrams.net, then File,
Export as, VSDX. In Miro, use Shapes and lines, then More shapes, then the Import diagram button,
and choose the `.vsdx` file. The shapes arrive as editable Miro objects with the lanes and arrows
in place.

Two things to know about this route. It needs the one manual export step, because Miro imports
`.vsdx` rather than `.drawio` directly. And the conversion does its own object mapping, so colours
and some styling may not come across exactly. The shapes here are deliberately plain for that
reason: rectangles, one diamond where there is a real decision, and dashed rules for the three
lines. **We have not been able to test this import, because it needs a Miro workspace. Try it on one
board before relying on it for a session.**

**Building the board through the API is the route to a fully laid out board.** Miro's REST API v2
has endpoints for frames, sticky notes and connectors at
`https://api.miro.com/v2/boards/{board_id}/`, and a short script could place every sticky and every
connector exactly. It needs an access token created in your own Miro developer settings, and the
board has to exist first. We have not written that script, because it cannot be tested from here and
an untested build script is worth less than the two routes above. If NHSBSA would find it useful, it
is a small piece of work and we can do it with a token.

**There is no CSV here, on purpose.** Miro's CSV import makes one sticky per row from mapped
columns, and does not keep a position. In a journey map or a blueprint the position is the content,
so the import would give you the right words in the wrong shape.

## Where the content comes from

Every cell in the four journeys, the four handoff maps, the grid and the assurance blueprint is
from the playbook. The journeys are the four role pages and the journey partial each one includes.
The assurance blueprint draws on the five phase pages, the role pages, deciding your assurance
level and Business Critical analysis. Each handoff map draws on the column for its level in what
your level requires, on the "who does what in this phase" table at the foot of each phase page,
and on the role pages. The levels are cumulative, so a lower level's requirement holds at a higher
one and never the other way round, and no board carries a requirement from a level above its own.

Nothing in them says anything about NHSBSA that the playbook does not already say. They are not a
record of a particular piece of work, and nothing in them says who did one or when.

The site blueprint is the exception, and it says so on its face: it describes the delivered site
rather than NHSBSA, which is why it can carry a lane about how the site is built and what the build
refuses to ship.

## Two readings worth challenging

**The assurance blueprint puts the commissioner in the customer lane.** That is a reading rather
than something the playbook states. It is the role the playbook gives them, arriving with a decision
to make and leaving with analysis they can use, and it is what makes the line of visibility mean
something: everything below it is work done for the commissioner and not in front of them. If
NHSBSA would rather see the blueprint drawn with the analyst as the customer of an assurance
service, that is a different and also defensible picture, and it is a short change to make.

**The journey maps carry a "watch out for" lane that the playbook tables do not have.** Each entry
in it is a warning the playbook already prints beside that stop, lifted into its own lane so that
the whole set can be read together. A stop the playbook does not warn about has nothing in that lane
rather than something invented for symmetry.

## What these are not

They have not been tested with an analyst, a commissioner or anybody using a screen reader. They are
a starting point for that conversation rather than the output of one.

The `.drawio` files are drawings, not the playbook. If one of them disagrees with a page, the page is
right and the drawing needs correcting. Both come from the same source file,
`build/build-service-design.py`, so a correction is made once.
