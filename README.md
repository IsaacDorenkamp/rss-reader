Untitled RSS Reader
-------------------

Description Pending

TODO
-------------------

* Infrastructure
    + Use `channel.link` as a primary identifier of a feed rather than `channel.ref`.
      Usage of `channel.ref` should be limited to cases where the exact location of
      the RSS feed is for purposes of fetching.
    + Re-evaluate the concurrency/task dispatching system. I feel like there is a
      better architecture for this system that allows for more flexibility and
      intuitive task chaining (like Promise chaining in JS) but the way it stands
      works well enough *for now*.
        - Might consider leveraging `concurrency.futures.ThreadPoolExecutor`!
    + More thorough logging: tasks should log significant progress checkpoints
        - "Significant progress checkpoints" include, at a minimum, task start
          and task completion (or task failure if applicable).
        - Ideally, There should be relatively clear delineation between log
          messages submitted by different tasks.
* GUI
    + Re-calculate size hints for list items when window is resized.
    + Ellipsize titles that are too long (adjusting with resize)
    + Ellipsize descriptions that exceed a certain limit (word count? height?)
    + Need some slick icons for a toolbar.
