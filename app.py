import os
import chainlit as cl
from langchain_core.runnables import RunnableConfig
from agent import setup_runnable

# Store image paths for visual assets
CULTURAL_IMAGE_PATH = "trad.jpeg"  # Image 1: Girls playing Hejla
RULES_IMAGE_PATH = "rules.png"  # Image 2: Illustrated Hejla squares and rules
HISTORY_IMAGE_PATH = "history.gif"  # Image 3: Historical context of Hejla
OPENER_IMAGE_PATH = "culture.png"  # Opener image

# Quiz questions database
QUIZ_QUESTIONS = [
    {
        "category": "rules",
        "question": "How many squares are traditionally used in Hejla?",
        "options": ["4 squares", "6 squares", "8 squares", "10 squares"],
        "correct": 2,
        "level": "novice"
    },
    {
        "category": "rules",
        "question": "How do you move through the squares in Hejla?",
        "options": ["Jump with both feet", "Hop on one foot", "Run through", "Walk normally"],
        "correct": 1,
        "level": "novice"
    },
    {
        "category": "gameplay",
        "question": "When hopping through squares, what must you do with the square containing the stone?",
        "options": ["Step on it", "Skip over it", "Pick it up", "Jump twice"],
        "correct": 1,
        "level": "beginner"
    },
    {
        "category": "culture",
        "question": "Hejla is traditionally played mostly by:",
        "options": ["Boys only", "Adults only", "Girls", "Elderly people"],
        "correct": 2,
        "level": "novice"
    },
    {
        "category": "equipment",
        "question": "What can you use to mark squares for Hejla?",
        "options": ["Chalk or scratching dirt", "Paint", "Tape", "Paper"],
        "correct": 0,
        "level": "beginner"
    },
    {
        "category": "gameplay",
        "question": "What happens if you step on a line?",
        "options": ["You get an extra turn", "You lose your turn", "You win", "Nothing happens"],
        "correct": 1,
        "level": "intermediate"
    },
    {
        "category": "rules",
        "question": "What do you do after completing all 8 turns?",
        "options": ["Start over", "End the game", "Throw stone behind you to create a 'home'", "Switch with another player"],
        "correct": 2,
        "level": "intermediate"
    },
    {
        "category": "strategy",
        "question": "What can you do when you have a 'home' square?",
        "options": ["Rest both feet", "Impose rules on other players", "Both A and B", "Nothing special"],
        "correct": 2,
        "level": "advanced"
    },
    {
        "category": "equipment",
        "question": "Which of these CANNOT be used as a throwing object in Hejla?",
        "options": ["Stone", "Coin", "Large ball", "Button"],
        "correct": 2,
        "level": "beginner"
    },
    {
        "category": "social",
        "question": "What makes Hejla a good community game?",
        "options": ["It's expensive", "It requires special equipment", "It's accessible anywhere with simple materials", "It's only for professionals"],
        "correct": 2,
        "level": "advanced"
    }
]

def get_topic_description(topic):
    """Get a friendly description of the topic and appropriate image"""
    topic_lower = topic.lower()

    # Default is no image
    image_path = None

    if "play" in topic_lower or "rules" in topic_lower or "how to" in topic_lower or "hop" in topic_lower:
        description = "Hejla gameplay and rules"
        image_path = RULES_IMAGE_PATH
    elif "history" in topic_lower or "origin" in topic_lower or "past" in topic_lower or "traditional" in topic_lower:
        description = "the history of Hejla"
        image_path = HISTORY_IMAGE_PATH
    elif "culture" in topic_lower or "tradition" in topic_lower or "girls" in topic_lower or "childhood" in topic_lower:
        description = "the cultural significance of Hejla"
        image_path = CULTURAL_IMAGE_PATH
    elif "square" in topic_lower or "ground" in topic_lower or "chalk" in topic_lower:
        description = "how to set up Hejla"
        image_path = RULES_IMAGE_PATH
    elif "home" in topic_lower or "winning" in topic_lower or "rules" in topic_lower:
        description = "Hejla rules and winning"
        image_path = RULES_IMAGE_PATH
    else:
        description = "Hejla"

    return description, image_path

async def select_relevant_quiz_questions(topic, count=3, user_level="novice"):
    """Select quiz questions relevant to the topic of conversation and user level"""
    # Map topic keywords to categories
    keyword_to_category = {
        "play": "rules", "rules": "rules", "how to": "rules", "hop": "gameplay",
        "stone": "equipment", "chalk": "equipment", "square": "rules",
        "girls": "culture", "tradition": "culture", "culture": "culture",
        "win": "strategy", "home": "strategy", "line": "gameplay"
    }

    # Determine categories based on keywords in topic
    categories = set()
    topic_lower = topic.lower()
    for keyword, category in keyword_to_category.items():
        if keyword in topic_lower:
            categories.add(category)

    # If no specific categories matched, use all categories
    if not categories:
        categories = {"rules", "gameplay", "culture", "equipment", "strategy", "social"}

    # Filter questions by selected categories
    category_questions = [q for q in QUIZ_QUESTIONS if q.get("category", "") in categories]

    # If no relevant questions by category, fall back to all questions
    if not category_questions:
        category_questions = QUIZ_QUESTIONS

    # Filter by user level or below
    available_levels = ["novice", "beginner"]  # Default levels
    if user_level == "beginner":
        available_levels = ["novice", "beginner"]
    elif user_level == "intermediate":
        available_levels = ["novice", "beginner", "intermediate"]
    elif user_level == "advanced":
        available_levels = ["novice", "beginner", "intermediate", "advanced"]

    # Filter questions by appropriate level
    level_questions = [q for q in category_questions if q.get("level", "novice") in available_levels]

    # If no questions at appropriate level, fall back to category questions
    if not level_questions:
        level_questions = category_questions

    # Select the requested number of questions
    import random
    selected = random.sample(level_questions, min(count, len(level_questions)))

    return selected

async def send_quiz_question(question_data):
    """Send a single quiz question with option buttons"""
    # Get current question number
    current_question = cl.user_session.get("current_quiz_question", 0)

    # Create option buttons
    actions = [
        cl.Action(
            name="quiz_answer",
            payload={"question": question_data["question"],
                     "selected_index": i,
                     "correct_index": question_data["correct"]},
            label=option
        ) for i, option in enumerate(question_data["options"])
    ]

    # Send the question
    question_text = f"**Quick Quiz Question {current_question + 1}!** 🤔\n\n{question_data['question']}"

    await cl.Message(
        content=question_text,
        actions=actions
    ).send()

async def send_follow_up_suggestions(topic):
    """Send follow-up suggestions based on the topic"""
    # Get user level
    user_level = cl.user_session.get("user_level", "novice")

    # Suggest appropriate follow-ups based on topic
    if "play" in topic or "rules" in topic or "how to" in topic or "hop" in topic:
        follow_ups = [
            {"question": "How do you draw the squares for Hejla?",
             "label": "Drawing squares"},
            {"question": "What's the hopping technique in Hejla?",
             "label": "Hopping tips"},
            {"question": "Can boys play Hejla too?",
             "label": "Who can play?"}
        ]
    elif "culture" in topic or "girls" in topic or "tradition" in topic:
        follow_ups = [
            {"question": "Why is Hejla important in Sudanese culture?",
             "label": "Cultural impact"},
            {"question": "Where do girls usually play Hejla?",
             "label": "Play locations"},
            {"question": "Is Hejla played in other countries too?",
             "label": "Regional variations"}
        ]
    elif "win" in topic or "home" in topic or "strategy" in topic:
        follow_ups = [
            {"question": "How do you create a 'home' in Hejla?",
             "label": "Creating homes"},
            {"question": "What rules can you make for your home?",
             "label": "Home rules"},
            {"question": "What's the best strategy to win?",
             "label": "Winning tips"}
        ]
    else:
        follow_ups = [
            {"question": "How do you play Hejla step by step?",
             "label": "Basic rules"},
            {"question": "What do you need to play Hejla?",
             "label": "Equipment needed"},
            {"question": "Can Hejla be played indoors?",
             "label": "Playing locations"}
        ]

    # Create action buttons
    actions = [
        cl.Action(
            name="dynamic_suggestion",
            payload={"question": item["question"]},
            label=item["label"]
        )
        for item in follow_ups
    ]

    # Add a quiz button
    actions.append(
        cl.Action(
            name="quiz_request",
            payload={"topic": topic, "level": user_level},
            label="Quick quiz?"
        )
    )

    # Send follow-up suggestions
    suggestion_msg = cl.Message(
        content="Want to chat about:",
        actions=actions
    )
    await suggestion_msg.send()

@cl.on_chat_start
async def on_chat_start():
    # Initialize user session
    cl.user_session.set("user_level", "novice")

    # First message
    intro_text = (
        "Hey! 👋\n\n"
        "I'm *Zola*, and I'm all about Hejla! 🦶\n"
        "What's your name? I'd love to chat about this awesome Sudanese hopscotch game!"
    )

    # Send introduction
    await cl.Message(content=intro_text).send()

    # Create image objects and store them in user session
    try:
        opener_image = cl.Image(path=OPENER_IMAGE_PATH, name="opener", display="inline")
        cultural_image = cl.Image(path=CULTURAL_IMAGE_PATH, name="hejla_cultural", display="inline")
        rules_image = cl.Image(path=RULES_IMAGE_PATH, name="hejla_rules", display="inline")
        history_image = cl.Image(path=HISTORY_IMAGE_PATH, name="hejla_history", display="inline")

        # Store media in user session
        cl.user_session.set("opener_image", opener_image)
        cl.user_session.set("cultural_image", cultural_image)
        cl.user_session.set("rules_image", rules_image)
        cl.user_session.set("history_image", history_image)
    except Exception as e:
        # Handle image loading errors gracefully
        print(f"Error loading images: {e}")
        await cl.Message(content="(Some visuals might not load, but we can still chat! 😊)").send()

    # Set flag to wait for user's name
    cl.user_session.set("waiting_for_name", True)

    # Setup runnable
    setup_runnable()

@cl.on_message
async def on_message(message: cl.Message):
    # Check if we're waiting for the user's name
    waiting_for_name = cl.user_session.get("waiting_for_name", False)

    if waiting_for_name:
        # Store the user's name
        user_name = message.content.strip()
        cl.user_session.set("user_name", user_name)
        cl.user_session.set("waiting_for_name", False)

        # Get the opener image from user session
        opener_image = cl.user_session.get("opener_image")

        # Welcome message
        welcome_text = (
            f"Nice to meet you, {user_name}! 🙌\n\n"
            "What would you like to know about Hejla? Pick something below or just ask me anything! 😊"
        )

        # Send welcome message with image if available
        if opener_image:
            welcome_msg = cl.Message(content=welcome_text, elements=[opener_image])
        else:
            welcome_msg = cl.Message(content=welcome_text)

        await welcome_msg.send()

        # Initial suggested questions
        actions = [
            cl.Action(
                name="dynamic_suggestion",
                payload={"question": "How do you play Hejla?"},
                label="How to play? 🦶"
            ),
            cl.Action(
                name="dynamic_suggestion",
                payload={"question": "How do you draw the squares for Hejla?"},
                label="Drawing squares? ➖"
            ),
            cl.Action(
                name="dynamic_suggestion",
                payload={"question": "Why is Hejla popular with girls?"},
                label="Cultural significance? 👧"
            ),
            cl.Action(
                name="dynamic_suggestion",
                payload={"question": "What makes a 'home' in Hejla?"},
                label="Creating homes? 🏠"
            ),
            cl.Action(
                name="dynamic_suggestion",
                payload={"question": "Can boys play Hejla too?"},
                label="Who can play? 🤝"
            )
        ]

        # Send message with actions
        suggestion_msg = cl.Message(content="What interests you?", actions=actions)
        await suggestion_msg.send()

        # Add a hint about visual explanations
        await cl.Message(content="(Ask about rules or 'how to play' and I'll show you with drawings! 🎨)").send()

    else:
        # Normal message handling
        runnable = cl.user_session.get("runnable")
        user_name = cl.user_session.get("user_name", "friend")
        user_level = cl.user_session.get("user_level", "novice")

        # Update context
        context = {
            "question": message.content,
            "user_name": user_name,
            "user_level": user_level
        }

        # Create a message for the response
        res = cl.Message(content="")

        # Stream the response
        async for chunk in runnable.astream(
                context,
                config=RunnableConfig(callbacks=[cl.LangchainCallbackHandler()])
        ):
            await res.stream_token(chunk)

        # Send the response
        await res.send()

        # Check if we should show an image based on the topic
        topic = message.content.lower()
        description, image_path = get_topic_description(topic)

        # Get appropriate image from user session based on topic
        topic_image = None
        if image_path == CULTURAL_IMAGE_PATH:
            topic_image = cl.user_session.get("cultural_image")
        elif image_path == RULES_IMAGE_PATH:
            topic_image = cl.user_session.get("rules_image")
        elif image_path == HISTORY_IMAGE_PATH:
            topic_image = cl.user_session.get("history_image")

        # If we have a relevant image, send it
        if topic_image:
            image_message = cl.Message(
                content=f"Here, check this out:",
                elements=[topic_image]
            )
            await image_message.send()

        # Send follow-up suggestions
        await send_follow_up_suggestions(topic)

# Quiz functionality
@cl.action_callback("quiz_request")
async def on_quiz_request(action):
    """Handle request for a quiz question"""
    topic = action.payload.get("topic", "")
    user_level = action.payload.get("level", "novice")

    # Store the topic for later use
    cl.user_session.set("quiz_topic", topic)

    # Select 3 relevant quiz questions
    questions = await select_relevant_quiz_questions(topic, count=3, user_level=user_level)
    if questions:
        # Store the quiz questions and initialize quiz state
        cl.user_session.set("quiz_questions", questions)
        cl.user_session.set("current_quiz_question", 0)
        cl.user_session.set("quiz_score", 0)
        cl.user_session.set("quiz_total", len(questions))

        # Start the quiz
        await cl.Message(content="Let's test your Hejla knowledge! 🦶").send()
        await send_quiz_question(questions[0])
    else:
        await cl.Message(content="Hmm, no quiz questions ready for this topic yet. Ask me something else! 😅").send()

@cl.action_callback("quiz_answer")
async def on_quiz_answer(action):
    """Handle quiz answer selection"""
    question = action.payload.get("question", "")
    selected_index = action.payload.get("selected_index", -1)
    correct_index = action.payload.get("correct_index", -1)
    topic = cl.user_session.get("quiz_topic", "")

    # Retrieve quiz state
    quiz_questions = cl.user_session.get("quiz_questions", [])
    current_question_index = cl.user_session.get("current_quiz_question", 0)
    quiz_score = cl.user_session.get("quiz_score", 0)

    # Check if answer is correct
    is_correct = selected_index == correct_index

    # Update score if correct
    if is_correct:
        quiz_score += 1
        cl.user_session.set("quiz_score", quiz_score)
        await cl.Message(content=f"Yes! Nailed it! 🎯").send()
    else:
        # Get correct option text
        correct_option = "Unknown"
        for q in quiz_questions:
            if q["question"] == question:
                correct_option = q["options"][correct_index]
                break
        await cl.Message(content=f"Ah, close! It's actually **{correct_option}** 😅").send()

    # Move to next question or finish quiz
    current_question_index += 1
    cl.user_session.set("current_quiz_question", current_question_index)

    # Check if we have more questions
    if current_question_index < len(quiz_questions) and current_question_index < 3:
        # Send next question
        await send_quiz_question(quiz_questions[current_question_index])
    else:
        # Quiz complete - show score
        score_percentage = quiz_score / min(len(quiz_questions), 3) * 100

        # Provide feedback
        if score_percentage >= 80:
            feedback = "You're pretty good at this! 🌟"
        elif score_percentage >= 50:
            feedback = "Not bad at all! Getting the hang of it 👍"
        else:
            feedback = "Hey, we all start somewhere! 😊"

        # Send quiz completion message
        await cl.Message(
            content=f"Quiz done! You got {quiz_score}/{min(len(quiz_questions), 3)} 🏆\n\n{feedback}").send()

        # After quiz is complete, show relevant follow-up suggestions
        await send_follow_up_suggestions(topic)

# Dynamic suggestion callback
@cl.action_callback("dynamic_suggestion")
async def on_dynamic_suggestion_action(action):
    """Handle clicks on dynamic suggestions"""
    question = action.payload.get("question", "")

    if question:
        # Get appropriate image based on the question content
        topic_image = None
        question_lower = question.lower()

        if "rules" in question_lower or "play" in question_lower or "how" in question_lower or "hop" in question_lower:
            topic_image = cl.user_session.get("rules_image")
        elif "squares" in question_lower or "draw" in question_lower or "chalk" in question_lower:
            topic_image = cl.user_session.get("rules_image")
        elif "girls" in question_lower or "cultural" in question_lower or "traditional" in question_lower:
            topic_image = cl.user_session.get("cultural_image")
        elif "home" in question_lower or "win" in question_lower or "strategy" in question_lower:
            topic_image = cl.user_session.get("rules_image")

        # Send the appropriate image first if available
        if topic_image:
            image_topic = ""
            if topic_image == cl.user_session.get("rules_image"):
                image_topic = "the squares and rules"
            elif topic_image == cl.user_session.get("cultural_image"):
                image_topic = "how girls play it"
            elif topic_image == cl.user_session.get("history_image"):
                image_topic = "where Hejla comes from"

            image_message = cl.Message(
                content=f"Here's a pic showing {image_topic}:",
                elements=[topic_image]
            )
            await image_message.send()

        # Add ASCII art hint for rules questions
        if "rules" in question_lower or "how" in question_lower or "play" in question_lower:
            await cl.Message(content="Let me draw this out for you! 📐").send()

        # Process the message
        await on_message(cl.Message(content=question))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8000))  # Use Render's PORT env variable
    cl.run(port=port, host="0.0.0.0")
