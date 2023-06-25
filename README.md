Untitled RSS Reader
-------------------

Description Pending

TODO
-------------------

* Infrastructure
    + Use `channel.link` as a primary identifier of a feed rather than `channel.ref`.
      Usage of `channel.ref` should be limited to cases where the exact location of
      the RSS feed is for purposes of fetching.
    + Need to keep track of "read" state SEPARATELY from the Channel entities saved
      in the cache. Items should be identified by channel along with either the GUID
      or title, whichever is available.
* GUI
    + Re-calculate size hints for list items when window is resized.
    + Ellipsize titles that are too long (adjusting with resize)
    + Ellipsize descriptions that exceed a certain limit (word count? height?)
    + Need some slick icons for a toolbar.
