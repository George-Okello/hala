from datetime import datetime
import json
import os
import chainlit as cl
from langchain_core.runnables import RunnableConfig

from agent import setup_runnable

# Store image paths for visual assets
CULTURAL_IMAGE_PATH = "culture.jpeg"  # Image 1: People playing Seega
RULES_IMAGE_PATH = "rules.jpeg"  # Image 2: Illustrated Seega board and rules
HISTORY_IMAGE_PATH = "history.gif"  # Image 3: Historical context of Seega
OPENER_IMAGE_PATH = "opener.webp"  # Opener image

# Quiz questions database
QUIZ_QUESTIONS = [
    {
        "category": "rules",
        "question": "What type of game is Seega?",
        "options": ["Card game", "Strategic board game", "Sports game", "Dice game"],
        "correct": 1,
        "level": "novice"
    },
    {
        "category": "history",
        "question": "In which country is Seega most traditionally associated?",
        "options": ["Egypt", "Sudan", "Both Egypt and Sudan", "Morocco"],
        "correct": 2,
        "level": "novice"
    },
    {
        "category": "rules",
        "question": "How many pieces does each player start with in traditional Seega?",
        "options": ["3 pieces", "6 pieces", "12 pieces", "24 pieces"],
        "correct": 2,
        "level": "novice"
    },
    {
        "category": "strategy",
        "question": "What is the main objective in Seega?",
        "options": ["Reach the other side", "Capture all opponent's pieces", "Make three in a row",
                    "Control the center"],
        "correct": 1,
        "level": "beginner"
    },
    {
        "category": "board",
        "question": "What is the traditional board size for Seega?",
        "options": ["3x3 grid", "5x5 grid", "8x8 grid", "10x10 grid"],
        "correct": 1,
        "level": "beginner"
    },
    {
        "category": "culture",
        "question": "What materials are traditionally used to make Seega pieces?",
        "options": ["Plastic only", "Stones, seeds, or pebbles", "Metal coins", "Paper cutouts"],
        "correct": 1,
        "level": "beginner"
    },
    {
        "category": "gameplay",
        "question": "In Seega, how do pieces typically move?",
        "options": ["Only diagonally", "Only forward", "Horizontally and vertically, one square at a time",
                    "In any direction like chess"],
        "correct": 2,
        "level": "intermediate"
    },
    {
        "category": "capture",
        "question": "How are pieces captured in Seega?",
        "options": ["By jumping over them", "By surrounding them", "By reaching them",
                    "There is no capturing in Seega"],
        "correct": 1,
        "level": "intermediate"
    },
    {
        "category": "history",
        "question": "Seega is related to which ancient game?",
        "options": ["Chess", "Nine Men's Morris/Mill", "Backgammon", "Go"],
        "correct": 1,
        "level": "intermediate"
    },
    {
        "category": "cultural_impact",
        "question": "What social role does Seega play in Sudanese culture?",
        "options": ["Only played in formal tournaments", "Community gathering and strategic thinking development",
                    "Religious ceremonies only", "Educational tool for mathematics only"],
        "correct": 1,
        "level": "advanced"
    }
]

# Reflection questions
REFLECTION_QUESTIONS = {
    "novice": [
        "How does Seega compare to other board games you've played?",
        "What's the most challenging part about learning Seega?",
        "Does the simplicity of the board make it easier or harder to play strategically?",
        "Why do you think Seega uses a 5x5 grid instead of larger boards?",
    ],
    "beginner": [
        "How does strategy in Seega differ from chess or checkers?",
        "What role does capturing play in your Seega strategy?",
        "Have you noticed patterns in how games typically develop?",
        "How important is controlling the center of the board?",
    ],
    "intermediate": [
        "What makes Seega a good game for developing logical thinking?",
        "How has playing Seega changed your approach to other board games?",
        "What cultural insights do you gain from traditional Sudanese games?",
        "How might Seega strategies apply to real-life problem solving?",
    ],
    "advanced": [
        "How does Seega reflect Sudanese cultural values and thinking?",
        "What role do traditional games play in preserving cultural identity?",
        "How might Seega be adapted for modern educational purposes?",
        "What makes Seega unique compared to similar games worldwide?",
    ]
}


def get_topic_description(topic):
    """Get a friendly description of the topic and appropriate image"""
    topic_lower = topic.lower()

    # Default is no image
    image_path = None

    if "play" in topic_lower or "rules" in topic_lower or "how to" in topic_lower or "move" in topic_lower:
        description = "Seega gameplay and rules"
        image_path = RULES_IMAGE_PATH
    elif "history" in topic_lower or "origin" in topic_lower or "past" in topic_lower or "ancient" in topic_lower:
        description = "the history of Seega"
        image_path = HISTORY_IMAGE_PATH
    elif "region" in topic_lower or "country" in topic_lower or "where" in topic_lower or "sudan" in topic_lower:
        description = "where Seega is played"
        image_path = CULTURAL_IMAGE_PATH
    elif "strategy" in topic_lower or "technique" in topic_lower or "winning" in topic_lower or "capture" in topic_lower:
        description = "Seega strategies and techniques"
        image_path = RULES_IMAGE_PATH
    elif "culture" in topic_lower or "tradition" in topic_lower:
        description = "the cultural significance of Seega"
        image_path = CULTURAL_IMAGE_PATH
    elif "board" in topic_lower or "grid" in topic_lower or "piece" in topic_lower:
        description = "the Seega board and pieces"
        image_path = RULES_IMAGE_PATH
    else:
        description = "Seega"

    return description, image_path


async def select_relevant_quiz_questions(topic, count=3, user_level="novice"):
    """Select quiz questions relevant to the topic of conversation and user level"""
    # Map topic keywords to categories
    keyword_to_category = {
        "play": "rules", "rules": "rules", "how to": "rules", "move": "gameplay",
        "strategy": "strategy", "capture": "capture", "piece": "rules",
        "history": "history", "origin": "history", "culture": "culture",
        "region": "history", "country": "history", "where": "history",
        "sudan": "history", "egypt": "history", "board": "board"
    }

    # Determine categories based on keywords in topic
    categories = set()
    topic_lower = topic.lower()
    for keyword, category in keyword_to_category.items():
        if keyword in topic_lower:
            categories.add(category)

    # If no specific categories matched, use all categories
    if not categories:
        categories = {"rules", "history", "culture", "strategy", "board", "gameplay", "capture"}

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


async def send_reflection_question(topic):
    """Send a reflection question based on the user's current level"""
    # Get user level
    user_level = cl.user_session.get("user_level", "novice")
    user_name = cl.user_session.get("user_name", "friend")

    # Get appropriate reflection questions for this level
    level_questions = REFLECTION_QUESTIONS.get(user_level, REFLECTION_QUESTIONS["novice"])

    # Select a question
    import random
    reflection_question = random.choice(level_questions)

    # Send as a message with a more conversational tone
    await cl.Message(
        content=f"Hey {user_name}, I'm curious... 🤔\n\n{reflection_question}\n\n(Just type whatever comes to mind - no pressure! 😊)",
    ).send()

    # Track that we're waiting for reflection
    cl.user_session.set("waiting_for_reflection", True)
    cl.user_session.set("current_reflection_question", reflection_question)


async def send_follow_up_suggestions(topic):
    """Send follow-up suggestions based on the topic"""
    # Get user level
    user_level = cl.user_session.get("user_level", "novice")

    # Suggest appropriate follow-ups based on topic
    if "play" in topic or "rules" in topic or "how to" in topic or "move" in topic:
        follow_ups = [
            {"question": "What are the best opening moves in Seega?",
             "label": "Opening strategies"},
            {"question": "How do you capture pieces effectively?",
             "label": "Capture techniques"},
            {"question": "What board materials work best?",
             "label": "Board making"}
        ]
    elif "history" in topic or "origin" in topic or "past" in topic:
        follow_ups = [
            {"question": "How is Seega connected to ancient games?",
             "label": "Historical links"},
            {"question": "Why did Seega survive through centuries?",
             "label": "Cultural preservation"},
            {"question": "What role did Seega play in Sudan's past?",
             "label": "Social history"}
        ]
    elif "strategy" in topic or "technique" in topic or "winning" in topic or "capture" in topic:
        follow_ups = [
            {"question": "How do you control the center effectively?",
             "label": "Center control"},
            {"question": "What are the most powerful piece positions?",
             "label": "Positional play"},
            {"question": "How do you set up capture traps?",
             "label": "Trap strategies"}
        ]
    else:
        follow_ups = [
            {"question": "How exactly do you set up a Seega board?",
             "label": "Game setup"},
            {"question": "What pieces work best for playing?",
             "label": "Traditional pieces"},
            {"question": "Is Seega good for all ages?",
             "label": "Social play"}
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
        "I'm Salam! I’m Amal (أمل), and I'm all about Seega! 🎯\n"
        "What's your name? I'd love to chat about this awesome Sudanese board game!"
    )

    # Send introduction
    await cl.Message(content=intro_text).send()

    # Create image objects and store them in user session
    try:
        opener_image = cl.Image(path=OPENER_IMAGE_PATH, name="opener", display="inline")
        cultural_image = cl.Image(path=CULTURAL_IMAGE_PATH, name="seega_cultural", display="inline")
        rules_image = cl.Image(path=RULES_IMAGE_PATH, name="seega_rules", display="inline")
        history_image = cl.Image(path=HISTORY_IMAGE_PATH, name="seega_history", display="inline")

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
    waiting_for_reflection = cl.user_session.get("waiting_for_reflection", False)

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
            "What would you like to know about Seega? Pick something below or just ask me anything! 😊"
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
                payload={"question": "How do you play Seega?"},
                label="How to play? 🎯"
            ),
            cl.Action(
                name="dynamic_suggestion",
                payload={"question": "What materials do you need for a Seega board?"},
                label="Making a board? 🎪"
            ),
            cl.Action(
                name="dynamic_suggestion",
                payload={"question": "What are the winning strategies in Seega?"},
                label="Best strategies? 🧠"
            ),
            cl.Action(
                name="dynamic_suggestion",
                payload={"question": "Where does Seega come from?"},
                label="The origin story? 📚"
            ),
            cl.Action(
                name="dynamic_suggestion",
                payload={"question": "Why is Seega important in Sudanese culture?"},
                label="Cultural significance? 🏛️"
            )
        ]

        # Send message with actions
        suggestion_msg = cl.Message(content="What interests you?", actions=actions)
        await suggestion_msg.send()

        # Add a hint about visual explanations
        await cl.Message(content="(Ask about rules or 'how to play' and I'll show you with drawings! 🎨)").send()

    elif waiting_for_reflection:
        # Handle reflection response
        reflection_question = cl.user_session.get("current_reflection_question", "")

        # Reset waiting flags
        cl.user_session.set("waiting_for_reflection", False)

        # Acknowledge reflection
        await cl.Message(
            content="Thanks for sharing! 😊 Really interesting perspective.\n\nWhat else would you like to know about Seega?"
        ).send()

        # Continue conversation
        await send_follow_up_suggestions("general")

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
        await cl.Message(content="Let's test your Seega knowledge! 🎮").send()
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

        # Add reflection question after quiz
        if quiz_score > 0:  # Only ask reflection if they got at least one right
            await send_reflection_question(topic)


# Dynamic suggestion callback
@cl.action_callback("dynamic_suggestion")
async def on_dynamic_suggestion_action(action):
    """Handle clicks on dynamic suggestions"""
    question = action.payload.get("question", "")

    if question:
        # Get appropriate image based on the question content
        topic_image = None
        question_lower = question.lower()

        if "rules" in question_lower or "play" in question_lower or "how" in question_lower or "move" in question_lower:
            topic_image = cl.user_session.get("rules_image")
        elif "materials" in question_lower or "board" in question_lower or "making" in question_lower:
            topic_image = cl.user_session.get("rules_image")
        elif "strategies" in question_lower or "winning" in question_lower or "capture" in question_lower:
            topic_image = cl.user_session.get("rules_image")
        elif "come from" in question_lower or "origin" in question_lower or "where" in question_lower:
            topic_image = cl.user_session.get("history_image")
        elif "culture" in question_lower or "important" in question_lower or "sudanese" in question_lower:
            topic_image = cl.user_session.get("cultural_image")

        # Send the appropriate image first if available
        if topic_image:
            image_topic = ""
            if topic_image == cl.user_session.get("rules_image"):
                image_topic = "the board and rules"
            elif topic_image == cl.user_session.get("cultural_image"):
                image_topic = "how people play it"
            elif topic_image == cl.user_session.get("history_image"):
                image_topic = "where Seega comes from"

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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    cl.run(port=port, host="0.0.0.0")