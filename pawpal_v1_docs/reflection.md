# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

- Briefly describe your initial UML design.
- What classes did you include, and what responsibilities did you assign to each?

The initial UML design consists of 4 classes. Owner, Pet, Task, and Scheduler. The Pet represents the animal that is being cared for. The Owner represents who is using the app and the time budget they have available. Task will contain the name, category, priority, and duration of a task. These classes will be a python dataclass as they only store data. Scheduler will help organize the tasks and help with making a prioritized, time-constrained daily care plan. It will include more methods and access information by having the Owner and a list of Tasks as an attribute, and also tracks tasks that didn't fit in the plan. 

**b. Design changes**

- Did your design change during implementation?
- If yes, describe at least one change and why you made it.


Yes, there were many design changes during implementation. When smart algortihms were added like sorting and filtering, then new methods were added to the different classes as needed. Some attributes were also added to certain clasees for an easier method implementation. One example would be adding a pet attribute to the Task class so it would be easier to track which pet a task was associated with. This was helpful when making a schedule so the owner can know which pet a task is associated with.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

1. One constraint the scheduler considers is time. Since generate_plan tracks the available minutes and skips any tasks where the total duration would exceed the time budget. The schduler also looks at priority, with  highest priority tasks are attempted to fit in first. And alreadu complete tasks can also be filtered out before scheduling.

2. Non-negotiables would matter first. So this would first give priority to the available minutes an owner had. Then the priorty of the tasks is important to know which tasks to priotize. 


**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

- One tradeoff was prioritzing smaller duration tasks with less priority to higher priority tasks with a longer duration. It is possible to complete more tasks throughout the day if priority status was not taken into consideration. However, this tradeoff is reasonable because it's more important to get high priority tasks done as they are an indication of what is necessary for the day. 

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

I used Claude Code for direct project help and chatGPT for logisitcal questions.
I found prompts with more context were more helpful. It helped the AI get a better understanding to what type of answer I was looking for. I also found asking the AI for its input was also helpful because it taught me to think broader and consider rare cases that might come up in the future.  

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

One moment where I did not accept an AI suggestion as-is was when brainstorming for the classes. CClaude Code suggested 5 classes, with DailyPlan being a new one. When considering it, I thought adding this class would make things more complicated to implement and just focused on the 4 classes that was recommended in the guide.  


---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

The tests covered task completion status, pet task list growth, chronological sorting, daily recurrence, conflict detection, and three edge cases: zero available minutes, double-completion, and next_occurrence dropping the pet name. These tests were important because they verify the core scheduling contract where the right tasks get planned, in the right order, for the right pet. 
Sorting and conflict detection tests were important since the weekly schedule UI depends on both being correct. The edge case tests mattered because two of them revealed real bugs already present in the code, not just theoretical failures. Without these tests, those bugs could silently corrupt a pet's task list or produce a schedule missing pet associations with no error raised.

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

I have a medium level of confidence. The app works and the basic needs function, but it is not perfect. The core scheduling behaviors — sorting, priority ordering, conflict detection, and daily recurrence — all work correctly and pass their tests. However, two real bugs were uncovered during testing: `complete_task` has no guard against being called twice, and `next_occurrence` silently drops the pet name, both of which could corrupt task data without raising an error.

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

I am most satisfied with adding improvments to the project. It was fun once the basic functionality was working to go back and look at areas of improvement as the app was used. It was also fun to learn what changes were needed and also learning ways to add a new feature with minimum change needed in the code. 

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

If I had another iteration, I would improve the available minutes and owner had during different days of the week. I would also work through and small logic bottlenecks that the AI suggested to be fixed. 

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?

An improtant thing I learned about designing systems is that going back and adding new methods or attributes to the original uml design is normal (instead of having everything planned in the beginning). But it is important to note that a strong basic features are thought out and reflected in the intial UML to make adding extra methods and attributes easier. 