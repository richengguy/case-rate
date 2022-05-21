# COVID-19 Case Rate Tracking

This repository is a COVID-19 tracker that performs some extra analysis on top
of the existing, published case data.  The tracker scrapes data from the
following sources:

* [John Hopkins CSSE COVID-19 dataset](https://github.com/CSSEGISandData/COVID-19)
* [Public Health Agency of Canada](https://www.canada.ca/en/public-health/services/diseases/2019-novel-coronavirus-infection.html#a1)
* [Public Health Ontario](https://data.ontario.ca/dataset/status-of-covid-19-cases-in-ontario)

## Why build yet another COVID-19 tracker?

There are a few different trackers out there, such as, in no particular order:

 * [JHU's Coronavirus Dashboard](https://systems.jhu.edu/research/public-health/ncov/)
 * [Our World in Data's Statistics and Research](https://ourworldindata.org/coronavirus)
 * [COVID19info.live](https://covid19info.live/)

However, these are, for the most part, reporting the raw case counts.  This is
useful information but can miss some important context.  This includes things
like the lag-time inherent to the testing.

For example, assume that a COVID-19 test takes between one to three days to get
a result (postive *or* negative).  Let's also assume that the *true* number of
confirmed cases looks like this, where doubling takes two days:

|   Day     | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|-----------|---|---|---|---|---|---|---|---|
| **Count** | 1 | 1 | 2 | 2 | 4 | 4 | 8 | 8 |
| **New**   | 1 | 0 | 1 | 0 | 2 | 0 | 4 | 0 |

However, if it takes a test between one to three days to get a result, then what
you observe will be:

|   Day     | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|-----------|---|---|---|---|---|---|---|---|---|
| **Count** | 0 | 1 | 1 | 1 | 1 | 4 | 4 | 6 | 8 |
| **New**   | 0 | 1 | 0 | 0 | 0 | 4 | 0 | 2 | 2 |

There appears to be a spike of four cases on day '6', even though the growth
rate hasn't changed.  Basically, you need to look at the number of cases over
the *expected* lag in order to get a true sense of where things are.  Otherwise,
you have an extended period where things look stable but actually aren't.

A lot of this was inspired by these two YouTube videos:

<a href="http://www.youtube.com/watch?feature=player_embedded&v=Kas0tIxDvrg
" target="_blank"><img src="http://img.youtube.com/vi/Kas0tIxDvrg/0.jpg"
alt="3Blue1Brown Exponential Growth" width="240" height="180" border="10" /></a>

<a href="http://www.youtube.com/watch?feature=player_embedded&v=fgBla7RepXU
" target="_blank"><img src="http://img.youtube.com/vi/fgBla7RepXU/0.jpg"
alt="It's Okay to be Smart" width="240" height="180" border="10" /></a>

They provide a good overview of the underlying mathematics behind an outbreak
and exponential growth in general.

## Generating Reports

The best way to set up the development environment is with
[Conda](https://conda.io/en/latest/).  case-rate is meant to run using a GitHub
Actions workflow and the commands below have not been tested on Windows.

Create and activate the environment with

```bash
$ conda env create
$ conda activate case-rate
```

Building the web interface requires NodeJS 16.x.  Install the node dependencies
with

```bash
$ npm ci
```

Build the reports with

```bash
$ make report
```

The HTML report will be in the `dist` folder.

There is also an example Jypter notebook ([algorithm.ipynb]) that shows how the
time series prediction works.  Running it locally will require installing some
extra packages into your environment, i.e.,

```bash
$ pip install jupyter matplotlib ipympl
```
